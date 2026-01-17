from flask import Flask, render_template, request, jsonify
import os
import csv
import json
import uuid
from datetime import datetime
import random
from question_generator import get_question_generator
from review_strategy import get_review_strategy

# Flask应用 - 指定模板和静态文件目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
app = Flask(__name__, template_folder=os.path.join(BASE_DIR, 'templates'))

# 配置
DATA_DIR = os.path.join(BASE_DIR, 'data')
ARTICLES_DIR = os.path.join(BASE_DIR, 'articles')
USER_CONFIG_FILE = os.path.join(BASE_DIR, 'user.md')

# 确保必要的目录存在
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(ARTICLES_DIR, exist_ok=True)


# ==================== 数据管理函数 ====================

def init_csv_files():
    """初始化CSV文件"""
    csv_files = {
        'user_profile.csv': ['user_id', 'learning_languages', 'current_language', 'total_practice_count', 'total_words_learned', 'created_at', 'last_practice'],
        'practice_history.csv': ['practice_id', 'timestamp', 'source_article', 'words_learned', 'question_count', 'correct_count', 'accuracy', 'difficulty', 'time_spent', 'language'],
        'question_history.csv': ['question_id', 'practice_id', 'timestamp', 'question_type', 'word', 'question_content', 'correct_answer', 'user_answer', 'is_correct', 'difficulty', 'language'],
        'word_progress.csv': ['word', 'language', 'total_attempts', 'correct_attempts', 'last_review', 'next_review', 'ease_factor', 'interval', 'mastery_level']
    }

    for filename, headers in csv_files.items():
        filepath = os.path.join(DATA_DIR, filename)
        if not os.path.exists(filepath):
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()


def get_user_profile():
    """
    获取用户配置
    Returns:
        dict: 包含用户配置的字典，包括 learning_languages (dict) 和 current_language (str)
    """
    if os.path.exists(USER_CONFIG_FILE):
        with open(USER_CONFIG_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
            # 简单解析Markdown格式的配置
            config = {}
            for line in content.split('\n'):
                if '：' in line or ': ' in line:
                    key, value = line.split('：' if '：' in line else ': ', 1)
                    config[key.strip().strip('-').strip()] = value.strip()

            # 解析 learning_languages JSON
            if 'learning_languages' in config:
                try:
                    config['learning_languages'] = json.loads(config['learning_languages'])
                except:
                    config['learning_languages'] = {}
            else:
                # 兼容旧格式：如果只有 preferred_language，转换为 learning_languages
                if '学习语言' in config:
                    lang = config['学习语言']
                    vocab_level = config.get('词汇量等级', '5')
                    config['learning_languages'] = {
                        lang: {
                            'level': int(vocab_level),
                            'daily_minutes': 15,
                            'practice_count': 0,
                            'words_learned': 0
                        }
                    }
                    # 设置当前语言
                    config['current_language'] = lang
                    # 保存新格式
                    save_user_profile_to_csv(config)
                else:
                    config['learning_languages'] = {}

            return config
    return None


def save_user_profile_to_csv(config):
    """将用户配置保存到CSV文件"""
    filepath = os.path.join(DATA_DIR, 'user_profile.csv')

    # 读取现有的用户记录（如果有）
    existing_records = []
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            existing_records = list(reader)

    # 准备数据
    learning_languages_json = json.dumps(config.get('learning_languages', {}), ensure_ascii=False)
    current_language = config.get('current_language', list(config.get('learning_languages', {}).keys())[0] if config.get('learning_languages') else '英语')

    # 计算总统计
    total_practice = sum(lang_data.get('practice_count', 0) for lang_data in config.get('learning_languages', {}).values())
    total_words = sum(lang_data.get('words_learned', 0) for lang_data in config.get('learning_languages', {}).values())

    if existing_records:
        # 更新现有记录
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['user_id', 'learning_languages', 'current_language', 'total_practice_count', 'total_words_learned', 'created_at', 'last_practice'])
            writer.writeheader()
            for record in existing_records:
                writer.writerow({
                    'user_id': record['user_id'],
                    'learning_languages': learning_languages_json,
                    'current_language': current_language,
                    'total_practice_count': total_practice,
                    'total_words_learned': total_words,
                    'created_at': record['created_at'],
                    'last_practice': datetime.now().isoformat()
                })
    else:
        # 创建新记录
        with open(filepath, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['user_id', 'learning_languages', 'current_language', 'total_practice_count', 'total_words_learned', 'created_at', 'last_practice'])
            writer.writerow({
                'user_id': str(uuid.uuid4()),
                'learning_languages': learning_languages_json,
                'current_language': current_language,
                'total_practice_count': total_practice,
                'total_words_learned': total_words,
                'created_at': datetime.now().isoformat(),
                'last_practice': datetime.now().isoformat()
            })


def save_user_profile(data):
    """
    保存用户配置（首次设置）
    Args:
        data: dict，包含 vocabulary_level, preferred_language, learning_goal, question_type_preference, daily_minutes
    """
    # 构建多语言配置
    language = data.get('preferred_language', '英语')
    level = int(data.get('vocabulary_level', '5'))
    daily_minutes = int(data.get('daily_minutes', '15'))

    learning_languages = {
        language: {
            'level': level,
            'daily_minutes': daily_minutes,
            'practice_count': 0,
            'words_learned': 0,
            'goal': data.get('learning_goal', '日常交流'),
            'question_preference': data.get('question_type_preference', '单选为主')
        }
    }

    config = {
        'learning_languages': learning_languages,
        'current_language': language
    }

    # 保存到 Markdown 文件（用于人类阅读）
    content = f"""# 用户特征

- learning_languages: {json.dumps(learning_languages, ensure_ascii=False)}
- current_language: {language}
- 学习目标: {data.get('learning_goal', '日常交流')}
- 偏好题型: {data.get('question_type_preference', '单选为主')}
- 每日学习时长: {daily_minutes}分钟
"""
    with open(USER_CONFIG_FILE, 'w', encoding='utf-8') as f:
        f.write(content)

    # 保存到 CSV
    save_user_profile_to_csv(config)


def adjust_difficulty_based_on_performance(user_config):
    """
    根据用户最近的正确率动态调整难度（针对当前语言）

    Args:
        user_config: 用户配置字典

    Returns:
        调整后的词汇量等级
    """
    current_language = user_config.get('current_language', '英语')
    learning_languages = user_config.get('learning_languages', {})

    # 获取当前语言的基础等级
    if current_language not in learning_languages:
        return 5  # 默认等级

    base_level = learning_languages[current_language].get('level', 5)

    # 读取最近的练习记录（最近5次，针对当前语言）
    filepath = os.path.join(DATA_DIR, 'practice_history.csv')
    if not os.path.exists(filepath):
        return base_level

    recent_accuracies = []
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        # 获取最近5次练习的准确率（仅针对当前语言）
        for row in rows[-5:]:
            try:
                # 检查语言是否匹配
                if row.get('language', '') == current_language:
                    acc = float(row['accuracy'])
                    recent_accuracies.append(acc)
            except (ValueError, KeyError):
                continue

    if not recent_accuracies:
        return base_level

    # 计算平均准确率
    avg_accuracy = sum(recent_accuracies) / len(recent_accuracies)

    # 动态调整难度
    adjusted_level = base_level

    if avg_accuracy >= 90:
        # 表现优秀，提升2级
        adjusted_level = min(10, base_level + 2)
    elif avg_accuracy >= 80:
        # 表现良好，提升1级
        adjusted_level = min(10, base_level + 1)
    elif avg_accuracy <= 40:
        # 表现较差，降低2级
        adjusted_level = max(1, base_level - 2)
    elif avg_accuracy <= 50:
        # 表现不太好，降低1级
        adjusted_level = max(1, base_level - 1)

    # 如果调整了难度，打印日志
    if adjusted_level != base_level:
        print(f"动态难度调整[{current_language}]：基础等级 {base_level} → 调整后等级 {adjusted_level}（基于平均准确率 {avg_accuracy:.1f}%）")

    return adjusted_level


def save_practice_history(practice_id, data):
    """保存练习历史"""
    filepath = os.path.join(DATA_DIR, 'practice_history.csv')
    with open(filepath, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['practice_id', 'timestamp', 'source_article', 'words_learned', 'question_count', 'correct_count', 'accuracy', 'difficulty', 'time_spent'])
        writer.writerow({
            'practice_id': practice_id,
            'timestamp': datetime.now().isoformat(),
            'source_article': data.get('source_article', ''),
            'words_learned': json.dumps(data.get('words_learned', [])),
            'question_count': data.get('question_count', 0),
            'correct_count': data.get('correct_count', 0),
            'accuracy': data.get('accuracy', 0),
            'difficulty': data.get('difficulty', 5),
            'time_spent': data.get('time_spent', 0)
        })


def save_question_history(practice_id, question_data):
    """保存题目历史"""
    filepath = os.path.join(DATA_DIR, 'question_history.csv')
    with open(filepath, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['question_id', 'practice_id', 'timestamp', 'question_type', 'word', 'question_content', 'correct_answer', 'user_answer', 'is_correct', 'difficulty'])
        writer.writerow({
            'question_id': str(uuid.uuid4()),
            'practice_id': practice_id,
            'timestamp': datetime.now().isoformat(),
            'question_type': question_data.get('type', ''),
            'word': question_data.get('word', ''),
            'question_content': question_data.get('question', ''),
            'correct_answer': question_data.get('answer', ''),
            'user_answer': question_data.get('user_answer', ''),
            'is_correct': question_data.get('is_correct', False),
            'difficulty': question_data.get('difficulty', 5)
        })


# ==================== 路由 ====================

@app.route('/')
def index():
    """主页"""
    if not os.path.exists(USER_CONFIG_FILE):
        return render_template('setup.html')
    return render_template('index.html')


@app.route('/languages')
def languages():
    """语言管理页面"""
    if not os.path.exists(USER_CONFIG_FILE):
        return render_template('setup.html')
    return render_template('languages.html')


@app.route('/result')
def result():
    """结果页面"""
    return render_template('result.html')


@app.route('/api/setup', methods=['POST'])
def setup():
    """保存用户配置"""
    try:
        data = request.json
        save_user_profile(data)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/languages', methods=['GET'])
def get_languages():
    """获取用户所有学习语言"""
    try:
        user_config = get_user_profile()
        if not user_config:
            return jsonify({'success': False, 'error': '用户配置不存在'}), 400

        learning_languages = user_config.get('learning_languages', {})
        current_language = user_config.get('current_language', '')

        # 为每种语言添加统计信息
        languages_with_stats = []
        for lang_name, lang_data in learning_languages.items():
            # 从 word_progress.csv 获取该语言的单词掌握情况
            mastered_words = 0
            learning_words = 0
            filepath = os.path.join(DATA_DIR, 'word_progress.csv')
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if row.get('language', '') == lang_name:
                            mastery_level = int(row.get('mastery_level', 0))
                            if mastery_level >= 4:
                                mastered_words += 1
                            else:
                                learning_words += 1

            languages_with_stats.append({
                'name': lang_name,
                'level': lang_data.get('level', 5),
                'daily_minutes': lang_data.get('daily_minutes', 15),
                'practice_count': lang_data.get('practice_count', 0),
                'words_learned': lang_data.get('words_learned', 0),
                'mastered_words': mastered_words,
                'learning_words': learning_words,
                'is_current': lang_name == current_language
            })

        return jsonify({
            'success': True,
            'languages': languages_with_stats,
            'current_language': current_language
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/languages/add', methods=['POST'])
def add_language():
    """添加新语言"""
    try:
        data = request.json
        language = data.get('language')
        level = int(data.get('level', 5))
        daily_minutes = int(data.get('daily_minutes', 15))

        if not language:
            return jsonify({'success': False, 'error': '语言名称不能为空'}), 400

        user_config = get_user_profile()
        if not user_config:
            return jsonify({'success': False, 'error': '用户配置不存在'}), 400

        learning_languages = user_config.get('learning_languages', {})

        # 检查是否已经添加过该语言
        if language in learning_languages:
            return jsonify({'success': False, 'error': '该语言已存在'}), 400

        # 添加新语言
        learning_languages[language] = {
            'level': level,
            'daily_minutes': daily_minutes,
            'practice_count': 0,
            'words_learned': 0,
            'goal': data.get('goal', '日常交流'),
            'question_preference': data.get('question_preference', '单选为主')
        }

        user_config['learning_languages'] = learning_languages

        # 保存到 CSV 和 Markdown 文件
        save_user_profile_to_csv(user_config)

        # 更新 Markdown 文件
        content = f"""# 用户特征

- learning_languages: {json.dumps(learning_languages, ensure_ascii=False)}
- current_language: {user_config.get('current_language', language)}
"""
        with open(USER_CONFIG_FILE, 'w', encoding='utf-8') as f:
            f.write(content)

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/languages/remove', methods=['POST'])
def remove_language():
    """移除语言"""
    try:
        data = request.json
        language = data.get('language')

        if not language:
            return jsonify({'success': False, 'error': '语言名称不能为空'}), 400

        user_config = get_user_profile()
        if not user_config:
            return jsonify({'success': False, 'error': '用户配置不存在'}), 400

        learning_languages = user_config.get('learning_languages', {})

        # 不能移除唯一语言
        if len(learning_languages) <= 1:
            return jsonify({'success': False, 'error': '不能移除唯一的学习语言'}), 400

        # 移除语言
        if language in learning_languages:
            del learning_languages[language]

            # 如果移除的是当前语言，切换到第一个语言
            if user_config.get('current_language') == language:
                user_config['current_language'] = list(learning_languages.keys())[0]

            user_config['learning_languages'] = learning_languages

            # 保存到 CSV 和 Markdown 文件
            save_user_profile_to_csv(user_config)

            # 更新 Markdown 文件
            content = f"""# 用户特征

- learning_languages: {json.dumps(learning_languages, ensure_ascii=False)}
- current_language: {user_config.get('current_language')}
"""
            with open(USER_CONFIG_FILE, 'w', encoding='utf-8') as f:
                f.write(content)

            return jsonify({'success': True, 'new_current': user_config.get('current_language')})

        return jsonify({'success': False, 'error': '语言不存在'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/languages/switch', methods=['POST'])
def switch_language():
    """切换当前学习语言"""
    try:
        data = request.json
        language = data.get('language')

        if not language:
            return jsonify({'success': False, 'error': '语言名称不能为空'}), 400

        user_config = get_user_profile()
        if not user_config:
            return jsonify({'success': False, 'error': '用户配置不存在'}), 400

        learning_languages = user_config.get('learning_languages', {})

        if language not in learning_languages:
            return jsonify({'success': False, 'error': '该语言不存在'}), 400

        # 切换语言
        user_config['current_language'] = language

        # 保存到 CSV 和 Markdown 文件
        save_user_profile_to_csv(user_config)

        # 更新 Markdown 文件
        content = f"""# 用户特征

- learning_languages: {json.dumps(learning_languages, ensure_ascii=False)}
- current_language: {language}
"""
        with open(USER_CONFIG_FILE, 'w', encoding='utf-8') as f:
            f.write(content)

        return jsonify({'success': True, 'current_language': language})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/generate_questions', methods=['POST'])
def generate_questions():
    """生成题目"""
    print("=== 开始生成题目 ===")
    try:
        # 获取用户配置
        print("1. 获取用户配置...")
        user_config = get_user_profile()
        if not user_config:
            print("错误: 用户配置不存在")
            return jsonify({'success': False, 'error': '用户配置不存在'}), 400
        print(f"用户配置: {user_config}")

        # 动态调整难度
        print("2. 调整难度...")
        adjusted_level = adjust_difficulty_based_on_performance(user_config)
        user_config['词汇量等级'] = str(adjusted_level)
        print(f"调整后的等级: {adjusted_level}")

        # 使用题目生成器生成题目
        print("3. 初始化题目生成器...")
        generator = get_question_generator(ARTICLES_DIR, DATA_DIR)
        print("4. 开始生成题目...")
        questions = generator.generate(user_config, count=15)
        print(f"5. 题目生成完成，共 {len(questions)} 道")

        practice_id = str(uuid.uuid4())
        print("=== 题目生成成功 ===")

        return jsonify({
            'success': True,
            'practice_id': practice_id,
            'questions': questions,
            'adjusted_level': adjusted_level  # 返回调整后的等级
        })
    except Exception as e:
        print(f"=== 题目生成失败: {e} ===")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/submit_answer', methods=['POST'])
def submit_answer():
    """提交答案"""
    try:
        data = request.json
        is_correct = data.get('is_correct', False)
        word = data.get('word', '')

        # 保存题目历史
        question_data = {
            'type': data.get('question_type', ''),
            'word': word,
            'question': data.get('question', ''),
            'answer': data.get('correct_answer', ''),
            'user_answer': data.get('user_answer', ''),
            'is_correct': is_correct,
            'difficulty': 5
        }
        save_question_history(data['practice_id'], question_data)

        # 更新单词进度（使用SM-2算法）
        if word:
            try:
                user_config = get_user_profile()
                language = user_config.get('学习语言', '英语') if user_config else '英语'

                review_strategy = get_review_strategy(DATA_DIR)
                review_strategy.update_word_progress(
                    word=word,
                    language=language,
                    is_correct=is_correct
                )
                print(f"已更新单词进度: {word}, 正确: {is_correct}")
            except Exception as e:
                print(f"更新单词进度失败: {e}")

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/practice_result', methods=['GET'])
def practice_result():
    """获取练习结果"""
    try:
        practice_id = request.args.get('practice_id')

        # 从question_history.csv中读取该练习的所有题目
        filepath = os.path.join(DATA_DIR, 'question_history.csv')
        questions = []

        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['practice_id'] == practice_id:
                        questions.append(row)

        # 计算统计数据
        total_count = len(questions)
        correct_count = sum(1 for q in questions if q['is_correct'] == 'True')
        accuracy = int((correct_count / total_count * 100)) if total_count > 0 else 0

        # 提取错题
        wrong_questions = []
        words_learned = set()

        for idx, q in enumerate(questions):
            if q['word']:
                words_learned.add(q['word'])
            if q['is_correct'] == 'False':
                wrong_questions.append({
                    'question_index': idx,
                    'type': q['question_type'],
                    'question': q['question_content'],
                    'user_answer': q['user_answer'],
                    'correct_answer': q['correct_answer'],
                    'explanation': ''  # AI解析功能待实现
                })

        return jsonify({
            'success': True,
            'total_count': total_count,
            'correct_count': correct_count,
            'accuracy': accuracy,
            'max_streak': 0,  # 待实现
            'words_learned': list(words_learned),
            'wrong_questions': wrong_questions
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/mastery_stats', methods=['GET'])
def mastery_stats():
    """获取单词掌握情况统计"""
    try:
        user_config = get_user_profile()
        language = user_config.get('学习语言', '英语') if user_config else '英语'

        review_strategy = get_review_strategy(DATA_DIR)
        stats = review_strategy.get_mastery_stats(language)

        return jsonify({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/get_explanation', methods=['POST'])
def get_explanation():
    """获取AI题目解析"""
    try:
        from ai_service import ai_service

        if ai_service is None:
            return jsonify({
                'success': False,
                'error': 'AI服务不可用'
            }), 500

        data = request.json
        question = data.get('question', '')
        user_answer = data.get('user_answer', '')
        correct_answer = data.get('correct_answer', '')
        question_type = data.get('question_type', '')
        word = data.get('word', '')

        # 构建prompt
        prompt = f"""请为以下题目提供详细的AI解析：

【题目】
{question}

【题目类型】
{question_type}

【核心词汇】
{word}

【正确答案】
{correct_answer}

【用户答案】
{user_answer}

【解析要求】
请提供一份详细的、教学性的解析，包括：

1. **正确答案解析**：
   - 为什么这是正确答案
   - 语法或词汇依据
   - 语境分析

2. **用户答案分析**：
   - 如果用户答对了：肯定并强化理解
   - 如果用户答错了：指出错误原因，常见陷阱

3. **知识点讲解**：
   - 核心词汇"{word}"的详细解释
   - 相关的语法点（如果适用）
   - 常见用法和搭配

4. **记忆技巧**：
   - 提供记忆该单词或语法点的方法
   - 实际应用场景

5. **拓展学习**：
   - 同义词或反义词（如果适用）
   - 相关表达或例句

解析应该：
- 用中文解释
- 亲切鼓励的语气
- 简洁但全面
- 适合学生理解
"""

        response = ai_service.client.chat.completions.create(
            model=ai_service.model,
            messages=[
                {"role": "system", "content": "你是一个耐心专业的语言教师，擅长用简单明了的方式解释语言知识点。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1000
        )

        explanation = response.choices[0].message.content.strip()

        return jsonify({
            'success': True,
            'explanation': explanation
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ==================== 辅助函数 ====================

def generate_default_questions():
    """生成默认题目（演示用）"""
    questions = [
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
    return questions


# ==================== 启动 ====================

if __name__ == '__main__':
    init_csv_files()
    app.run(debug=True)
