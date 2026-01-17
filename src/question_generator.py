"""
题目生成模块
协调AI服务和复习策略，生成完整的题目集
"""

import os
import random
from ai_service import ai_service
from review_strategy import get_review_strategy


class QuestionGenerator:
    """题目生成器"""

    def __init__(self, articles_dir, data_dir):
        """
        初始化题目生成器

        Args:
            articles_dir: 文章目录路径
            data_dir: 数据目录路径
        """
        self.articles_dir = articles_dir
        self.data_dir = data_dir

    def get_random_article(self):
        """
        随机选择一篇文章

        Returns:
            文章内容字符串，如果没有文章则返回None
        """
        articles = [f for f in os.listdir(self.articles_dir) if f.endswith('.txt')]

        if not articles:
            return None

        random_article = random.choice(articles)
        article_path = os.path.join(self.articles_dir, random_article)

        try:
            with open(article_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return content
        except Exception as e:
            print(f"读取文章失败: {e}")
            return None

    def generate(self, user_config, count=15):
        """
        生成题目（混合新题和复习题）

        Args:
            user_config: 用户配置字典
            count: 题目数量

        Returns:
            题目列表
        """
        all_questions = []
        language = user_config.get('学习语言', '英语')

        # 1. 获取需要复习的单词（最多5个）
        try:
            review_strategy = get_review_strategy(self.data_dir)
            words_due = review_strategy.get_words_due_for_review(language, limit=5)
            review_count = len(words_due)
            print(f"需要复习的单词: {review_count}个")
        except Exception as e:
            print(f"获取复习单词失败: {e}")
            words_due = []
            review_count = 0

        # 2. 为复习单词生成题目
        if review_count > 0 and ai_service is not None:
            review_questions = self._generate_review_questions(words_due, user_config)
            all_questions.extend(review_questions)

        # 3. 生成新题
        new_count = count - len(all_questions)
        if new_count > 0:
            new_questions = self._generate_new_questions(user_config, new_count)
            all_questions.extend(new_questions)

        # 4. 混合题目
        random.shuffle(all_questions)

        # 5. 确保题目数量
        if len(all_questions) < count:
            print(f"题目数量不足，补充默认题目")
            default_questions = self._get_default_questions()
            needed = count - len(all_questions)
            all_questions.extend(default_questions[:needed])

        return all_questions[:count]

    def _generate_review_questions(self, words_due, user_config):
        """
        为复习单词生成题目

        Args:
            words_due: 需要复习的单词列表
            user_config: 用户配置

        Returns:
            复习题列表
        """
        review_questions = []

        for word_data in words_due:
            word = word_data['word']

            # 为每个复习单词生成1-2道题
            try:
                prompt = f"""请为单词 "{word}" 生成1-2道复习题。

学生信息：
- 词汇量等级：{user_config.get('词汇量等级', '5')}/10
- 该单词的掌握程度：{float(word_data['mastery_level']) * 100:.0f}%
- 该单词已练习{word_data['total_attempts']}次，正确{word_data['correct_attempts']}次

要求：
1. 题目要帮助学生回忆和巩固该单词
2. 可以是选择题或填空题
3. 如果掌握程度较低，题目应该更简单
4. 提供简短的解析

请以JSON格式返回：
[
  {{
    "type": "multiple_choice" 或 "fill_blank",
    "question": "题目内容",
    "hint": "提示（可选）",
    "options": ["选项A", "选项B", "选项C", "选项D"],  // 仅单选题需要
    "answer": "正确答案",
    "explanation": "解析",
    "word": "{word}",
    "difficulty": 3
  }}
]
"""

                response = ai_service.client.chat.completions.create(
                    model=ai_service.model,
                    messages=[
                        {"role": "system", "content": "你是一个专业的语言教师，擅长设计复习题。"},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=800
                )

                content = response.choices[0].message.content.strip()

                # 提取JSON
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()

                import json
                questions = json.loads(content)

                for q in questions:
                    if self._validate_question(q):
                        review_questions.append(q)

            except Exception as e:
                print(f"生成复习题失败 ({word}): {e}")
                # 使用默认复习题
                review_questions.append(self._get_default_review_question(word))

        return review_questions

    def _generate_new_questions(self, user_config, count):
        """
        生成新题

        Args:
            user_config: 用户配置
            count: 题目数量

        Returns:
            新题列表
        """
        # 获取文章
        article_content = self.get_random_article()

        if not article_content:
            print("没有找到文章，使用默认题目")
            return self._get_default_questions()[:count]

        # 如果AI服务不可用，使用默认题目
        if ai_service is None:
            print("AI服务不可用，使用默认题目")
            return self._get_default_questions()[:count]

        # 使用AI生成题目
        try:
            questions = ai_service.generate_questions(article_content, user_config, count)

            if questions and len(questions) > 0:
                # 验证题目格式
                validated_questions = []
                for q in questions:
                    if self._validate_question(q):
                        validated_questions.append(q)

                # 如果生成的题目不够，补充默认题目
                if len(validated_questions) < count:
                    print(f"AI生成的题目数量不足，已生成{len(validated_questions)}题")
                    default_questions = self._get_default_questions()
                    needed = count - len(validated_questions)
                    validated_questions.extend(default_questions[:needed])

                return validated_questions[:count]
            else:
                print("AI未生成有效题目，使用默认题目")
                return self._get_default_questions()[:count]

        except Exception as e:
            print(f"生成题目失败: {e}")
            return self._get_default_questions()[:count]

    def _get_default_review_question(self, word):
        """
        获取默认复习题

        Args:
            word: 单词

        Returns:
            默认复习题
        """
        return {
            'type': 'multiple_choice',
            'question': f'请复习单词：{word}',
            'hint': '这是一个复习题目',
            'options': [f'{word} (正确)', '选项B', '选项C', '选项D'],
            'answer': f'{word} (正确)',
            'explanation': f'复习单词：{word}',
            'word': word,
            'difficulty': 3
        }

    def _validate_question(self, question):
        """
        验证题目格式是否正确

        Args:
            question: 题目字典

        Returns:
            是否有效
        """
        required_fields = ['type', 'question', 'answer', 'word']

        # 检查必需字段
        for field in required_fields:
            if field not in question:
                return False

        # 检查题型
        if question['type'] == 'multiple_choice':
            if 'options' not in question or not isinstance(question['options'], list):
                return False
            if len(question['options']) != 4:
                return False
            if question['answer'] not in question['options']:
                return False

        return True

    def _get_default_questions(self):
        """
        获取默认题目（当AI不可用时使用）

        Returns:
            默认题目列表
        """
        return [
            {
                'type': 'multiple_choice',
                'question': '请选择 "happy" 的中文释义',
                'hint': '这是一个常用的形容词',
                'options': ['悲伤的', '快乐的', '愤怒的', '疲惫的'],
                'answer': '快乐的',
                'explanation': 'Happy是一个常用的英语单词，意思是"快乐的、幸福的"。',
                'word': 'happy',
                'difficulty': 3
            },
            {
                'type': 'multiple_choice',
                'question': '请选择 "beautiful" 的中文释义',
                'hint': '用来形容美好事物的形容词',
                'options': ['丑陋的', '美丽的', '普通的', '奇怪的'],
                'answer': '美丽的',
                'explanation': 'Beautiful意为"美丽的、漂亮的"。',
                'word': 'beautiful',
                'difficulty': 4
            },
            {
                'type': 'fill_blank',
                'question': '完成句子：I am very _____ today.',
                'hint': '填写一个表示"开心"的单词',
                'answer': 'happy',
                'explanation': '这句话的意思是"我今天很开心"。',
                'word': 'happy',
                'difficulty': 3
            },
            {
                'type': 'multiple_choice',
                'question': '请选择 "run" 的中文释义',
                'hint': '这是一个动作动词',
                'options': ['走', '跑', '跳', '飞'],
                'answer': '跑',
                'explanation': 'Run是一个常用的动词，意思是"跑、奔跑"。',
                'word': 'run',
                'difficulty': 2
            },
            {
                'type': 'fill_blank',
                'question': '完成句子：She likes to _____ in the park.',
                'hint': '填写一个表示"跑步"的单词',
                'answer': 'run',
                'explanation': '这句话的意思是"她喜欢在公园里跑步"。',
                'word': 'run',
                'difficulty': 2
            },
            {
                'type': 'multiple_choice',
                'question': '请选择 "book" 的中文释义',
                'hint': '这是一个常用的名词',
                'options': ['书', '笔', '桌子', '椅子'],
                'answer': '书',
                'explanation': 'Book意为"书、书籍"。',
                'word': 'book',
                'difficulty': 1
            },
            {
                'type': 'fill_blank',
                'question': '完成句子：This is a good _____.',
                'hint': '填写一个表示"书"的单词',
                'answer': 'book',
                'explanation': '这句话的意思是"这是一本好书"。',
                'word': 'book',
                'difficulty': 1
            },
            {
                'type': 'multiple_choice',
                'question': '请选择 "eat" 的中文释义',
                'hint': '这是一个日常动作',
                'options': ['喝', '吃', '睡', '玩'],
                'answer': '吃',
                'explanation': 'Eat是一个基本动词，意思是"吃"。',
                'word': 'eat',
                'difficulty': 1
            },
            {
                'type': 'fill_blank',
                'question': '完成句子：Let\'s _____ dinner together.',
                'hint': '填写一个表示"吃"的单词',
                'answer': 'eat',
                'explanation': '这句话的意思是"让我们一起吃晚餐吧"。',
                'word': 'eat',
                'difficulty': 1
            },
            {
                'type': 'multiple_choice',
                'question': '请选择 "sleep" 的中文释义',
                'hint': '每个人每天都要做的事情',
                'options': ['工作', '睡觉', '运动', '学习'],
                'answer': '睡觉',
                'explanation': 'Sleep意为"睡觉"。',
                'word': 'sleep',
                'difficulty': 1
            },
            {
                'type': 'fill_blank',
                'question': '完成句子：I need to _____ now.',
                'hint': '填写一个表示"睡觉"的单词',
                'answer': 'sleep',
                'explanation': '这句话的意思是"我现在需要睡觉"。',
                'word': 'sleep',
                'difficulty': 1
            },
            {
                'type': 'multiple_choice',
                'question': '请选择 "write" 的中文释义',
                'hint': '与笔有关',
                'options': ['读', '写', '看', '听'],
                'answer': '写',
                'explanation': 'Write意为"写、书写"。',
                'word': 'write',
                'difficulty': 2
            },
            {
                'type': 'fill_blank',
                'question': '完成句子：Please _____ your name here.',
                'hint': '填写一个表示"写"的单词',
                'answer': 'write',
                'explanation': '这句话的意思是"请在这里写下你的名字"。',
                'word': 'write',
                'difficulty': 2
            },
            {
                'type': 'multiple_choice',
                'question': '请选择 "speak" 的中文释义',
                'hint': '与嘴巴有关',
                'options': ['听', '说', '读', '写'],
                'answer': '说',
                'explanation': 'Speak意为"说、说话"。',
                'word': 'speak',
                'difficulty': 2
            },
            {
                'type': 'fill_blank',
                'question': '完成句子：Can you _____ English?',
                'hint': '填写一个表示"说"的单词',
                'answer': 'speak',
                'explanation': '这句话的意思是"你会说英语吗？"。',
                'word': 'speak',
                'difficulty': 2
            }
        ]


# 创建全局实例
def get_question_generator(articles_dir, data_dir):
    """获取题目生成器实例"""
    return QuestionGenerator(articles_dir, data_dir)
