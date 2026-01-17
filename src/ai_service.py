"""
AI服务模块
提供题目生成、答案解析、翻译等功能
"""

import os
from openai import OpenAI
from dotenv import load_dotenv

# 加载环境变量 - 明确指定项目根目录的.env文件
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, '.env'))


class AIService:
    """AI服务类"""

    def __init__(self):
        """初始化AI服务"""
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.base_url = os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1')
        self.model = os.getenv('OPENAI_MODEL', 'gpt-4')

        if not self.api_key:
            raise ValueError("OPENAI_API_KEY 环境变量未设置")

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )

    def generate_questions(self, article_content, user_config, count=15):
        """
        使用 function calling 生成题目

        Args:
            article_content: 文章内容
            user_config: 用户配置字典
            count: 题目数量

        Returns:
            题目列表
        """
        vocab_level = user_config.get('词汇量等级', '5')
        language = user_config.get('学习语言', '英语')
        learning_goal = user_config.get('学习目标', '日常交流')

        # 定义 function schema
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "create_questions",
                    "description": f"根据文章内容创建{count}道{language}练习题",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "questions": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "type": {
                                            "type": "string",
                                            "enum": ["multiple_choice", "fill_blank"],
                                            "description": "题目类型"
                                        },
                                        "question": {
                                            "type": "string",
                                            "description": "题目内容"
                                        },
                                        "hint": {
                                            "type": "string",
                                            "description": "提示信息（可选）"
                                        },
                                        "options": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                            "description": "选项（仅单选题需要，4个选项）",
                                            "minItems": 4,
                                            "maxItems": 4
                                        },
                                        "answer": {
                                            "type": "string",
                                            "description": "正确答案"
                                        },
                                        "explanation": {
                                            "type": "string",
                                            "description": "详细解析"
                                        },
                                        "word": {
                                            "type": "string",
                                            "description": "核心词汇"
                                        },
                                        "difficulty": {
                                            "type": "integer",
                                            "minimum": 1,
                                            "maximum": 10,
                                            "description": "难度等级（1-10）"
                                        }
                                    },
                                    "required": ["type", "question", "answer", "explanation", "word", "difficulty"]
                                }
                            }
                        },
                        "required": ["questions"]
                    }
                }
            }
        ]

        prompt = f"""请根据以下文章内容，为词汇量等级{vocab_level}/10的学生生成{count}道练习题。

文章内容：
{article_content}

学习目标：{learning_goal}

要求：
1. 单选题和填空题混合
2. 从文章中选择3-5个核心词汇出题
3. 每道题要有详细解析
4. 难度适合词汇量等级{vocab_level}的学生

请调用 create_questions 函数来创建题目。"""

        try:
            print(f"正在调用AI生成{count}道题目...")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": f"你是一个专业的{language}语言教学专家。"},
                    {"role": "user", "content": prompt}
                ],
                tools=tools,
                tool_choice={"type": "function", "function": {"name": "create_questions"}},
                temperature=0.7,
                timeout=30.0  # 30秒超时
            )

            # 提取 function call 结果
            tool_call = response.choices[0].message.tool_calls[0]
            import json
            function_args = json.loads(tool_call.function.arguments)
            questions = function_args.get("questions", [])

            print(f"AI成功生成{len(questions)}道题目")
            return questions

        except Exception as e:
            print(f"AI生成题目失败: {e}")
            return None

    def check_answer(self, question, user_answer):
        """
        使用AI判断答案是否正确

        Args:
            question: 题目字典
            user_answer: 用户答案

        Returns:
            (is_correct, explanation) 是否正确和解析
        """
        prompt = f"""请判断以下答案是否正确：

题目：{question['question']}
正确答案：{question['answer']}
用户答案：{user_answer}

要求：
1. 判断用户答案是否正确（考虑拼写错误、同义词等情况）
2. 如果错误，提供简短的解析

请以JSON格式返回：
{{
    "is_correct": true/false,
    "explanation": "解析内容"
}}
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一个专业的语言教师。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )

            content = response.choices[0].message.content.strip()

            # 提取JSON
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            import json
            result = json.loads(content)
            return result.get('is_correct', False), result.get('explanation', '')

        except Exception as e:
            print(f"AI判题失败: {e}")
            # 如果AI判题失败，回退到简单的字符串匹配
            is_correct = str(user_answer).strip().lower() == str(question['answer']).strip().lower()
            return is_correct, ''

    def get_explanation(self, question, user_answer):
        """
        获取题目解析

        Args:
            question: 题目字典
            user_answer: 用户答案

        Returns:
            解析文本
        """
        if user_answer == question['answer']:
            return question.get('explanation', '回答正确！')

        prompt = f"""请为以下题目提供详细的解析：

题目：{question['question']}
正确答案：{question['answer']}
用户答案：{user_answer}

请解释：
1. 为什么正确答案是正确的
2. 用户答案可能存在的问题
3. 相关的语法或词汇知识点

解析应该简洁明了，适合学生理解。
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一个耐心的语言教师。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=500
            )

            explanation = response.choices[0].message.content.strip()
            return explanation

        except Exception as e:
            print(f"AI生成解析失败: {e}")
            return question.get('explanation', '')


# 创建全局实例
try:
    ai_service = AIService()
except Exception as e:
    print(f"警告: AI服务初始化失败 - {e}")
    ai_service = None
