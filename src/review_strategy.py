"""
复习策略模块
实现SM-2间隔重复算法
"""

import os
import csv
import uuid
from datetime import datetime, timedelta


class SM2Algorithm:
    """
    SM-2 (SuperMemo 2) 间隔重复算法实现

    算法原理：
    - EF (Ease Factor): 轻松度因子，表示记忆难度，默认2.5
    - Interval: 复习间隔（天数）
    - Repetitions: 重复次数
    """

    # 最小轻松度因子
    MIN_EF = 1.3

    @staticmethod
    def calculate_next_review(quality, easiness_factor, interval, repetitions):
        """
        计算下次复习时间

        Args:
            quality: 答题质量 (0-5)
                5 - 完美回忆，毫不犹豫
                4 - 正确但有点犹豫
                3 - 正确但很困难
                2 - 不正确，但看起来熟悉
                1 - 不正确，完全不记得
                0 - 不正确，甚至想不起来见过
            easiness_factor: 当前轻松度因子
            interval: 当前间隔（天数）
            repetitions: 当前重复次数

        Returns:
            (new_easiness_factor, new_interval, new_repetitions, next_review_date)
        """
        # 更新轻松度因子
        # EF' = EF + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
        new_easiness_factor = easiness_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
        new_easiness_factor = max(new_easiness_factor, SM2Algorithm.MIN_EF)

        # 更新重复次数和间隔
        if quality < 3:
            # 答错了，重新开始
            new_repetitions = 0
            new_interval = 1
        else:
            # 答对了
            new_repetitions = repetitions + 1

            if new_repetitions == 1:
                new_interval = 1
            elif new_repetitions == 2:
                new_interval = 6
            else:
                # I(n) = I(n-1) * EF
                new_interval = int(interval * new_easiness_factor)

        # 计算下次复习日期
        next_review_date = datetime.now() + timedelta(days=new_interval)

        return new_easiness_factor, new_interval, new_repetitions, next_review_date

    @staticmethod
    def quality_from_performance(is_correct, time_spent=None):
        """
        根据答题表现计算质量分数

        Args:
            is_correct: 是否正确
            time_spent: 答题耗时（秒），可选

        Returns:
            质量分数 (0-5)
        """
        if not is_correct:
            # 错误答案
            return 2  # 假设看起来熟悉但不正确

        # 正确答案
        if time_spent is None:
            return 4  # 默认：正确但有点犹豫

        # 根据答题时间判断质量
        if time_spent < 3:
            return 5  # 完美回忆，快速
        elif time_spent < 10:
            return 4  # 正确但有点犹豫
        else:
            return 3  # 正确但很困难


class ReviewStrategy:
    """复习策略管理"""

    def __init__(self, data_dir):
        """
        初始化复习策略

        Args:
            data_dir: 数据目录路径
        """
        self.data_dir = data_dir
        self.word_progress_file = os.path.join(data_dir, 'word_progress.csv')

        # 确保文件存在
        self._init_csv_file()

    def _init_csv_file(self):
        """初始化CSV文件"""
        if not os.path.exists(self.word_progress_file):
            with open(self.word_progress_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=[
                    'word', 'language', 'total_attempts', 'correct_attempts',
                    'last_review', 'next_review', 'ease_factor', 'interval', 'mastery_level'
                ])
                writer.writeheader()

    def get_words_due_for_review(self, language, limit=5):
        """
        获取今天需要复习的单词

        Args:
            language: 语言
            limit: 最大数量

        Returns:
            需要复习的单词列表
        """
        if not os.path.exists(self.word_progress_file):
            return []

        words_due = []
        now = datetime.now()

        with open(self.word_progress_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # 只返回指定语言的单词
                if row['language'] != language:
                    continue

                # 检查是否到了复习时间
                try:
                    next_review = datetime.fromisoformat(row['next_review'])
                    if next_review <= now:
                        words_due.append(row)
                except (ValueError, KeyError):
                    continue

                if len(words_due) >= limit:
                    break

        return words_due

    def update_word_progress(self, word, language, is_correct, time_spent=None):
        """
        更新单词学习进度

        Args:
            word: 单词
            language: 语言
            is_correct: 是否正确
            time_spent: 答题耗时（秒），可选
        """
        # 读取现有数据
        word_data = self._get_word_data(word, language)

        if word_data is None:
            # 新单词
            quality = SM2Algorithm.quality_from_performance(is_correct, time_spent)
            ef, interval, repetitions, next_review = SM2Algorithm.calculate_next_review(
                quality, 2.5, 0, 0  # 初始EF=2.5
            )

            word_data = {
                'word': word,
                'language': language,
                'total_attempts': 1,
                'correct_attempts': 1 if is_correct else 0,
                'last_review': datetime.now().isoformat(),
                'next_review': next_review.isoformat(),
                'ease_factor': ef,
                'interval': interval,
                'mastery_level': 1.0 if is_correct else 0.0
            }
        else:
            # 更新现有单词
            total_attempts = int(word_data['total_attempts']) + 1
            correct_attempts = int(word_data['correct_attempts']) + (1 if is_correct else 0)

            # 计算掌握程度
            mastery_level = correct_attempts / total_attempts

            # 使用SM-2算法
            quality = SM2Algorithm.quality_from_performance(is_correct, time_spent)
            ef, interval, repetitions, next_review = SM2Algorithm.calculate_next_review(
                quality,
                float(word_data['ease_factor']),
                int(word_data['interval']),
                0  # repetitions暂时不存储
            )

            word_data.update({
                'total_attempts': total_attempts,
                'correct_attempts': correct_attempts,
                'last_review': datetime.now().isoformat(),
                'next_review': next_review.isoformat(),
                'ease_factor': ef,
                'interval': interval,
                'mastery_level': mastery_level
            })

        # 保存到文件
        self._save_word_data(word_data)

    def _get_word_data(self, word, language):
        """
        获取单词数据

        Args:
            word: 单词
            language: 语言

        Returns:
            单词数据字典，如果不存在则返回None
        """
        if not os.path.exists(self.word_progress_file):
            return None

        with open(self.word_progress_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['word'] == word and row['language'] == language:
                    return row

        return None

    def _save_word_data(self, word_data):
        """
        保存单词数据

        Args:
            word_data: 单词数据字典
        """
        # 先读取所有数据
        rows = []
        updated = False

        if os.path.exists(self.word_progress_file):
            with open(self.word_progress_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = list(reader)

        # 更新或添加数据
        for i, row in enumerate(rows):
            if row['word'] == word_data['word'] and row['language'] == word_data['language']:
                rows[i] = word_data
                updated = True
                break

        if not updated:
            rows.append(word_data)

        # 写回文件
        with open(self.word_progress_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'word', 'language', 'total_attempts', 'correct_attempts',
                'last_review', 'next_review', 'ease_factor', 'interval', 'mastery_level'
            ])
            writer.writeheader()
            writer.writerows(rows)

    def get_mastery_stats(self, language=None):
        """
        获取掌握情况统计

        Args:
            language: 语言（可选），如果不指定则统计所有语言

        Returns:
            统计数据字典
        """
        if not os.path.exists(self.word_progress_file):
            return {
                'total_words': 0,
                'mastered_words': 0,
                'learning_words': 0,
                'average_mastery': 0.0
            }

        total_words = 0
        mastered_words = 0  # 掌握度 >= 0.8
        learning_words = 0  # 掌握度 < 0.8
        total_mastery = 0.0

        with open(self.word_progress_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if language and row['language'] != language:
                    continue

                total_words += 1
                mastery = float(row['mastery_level'])
                total_mastery += mastery

                if mastery >= 0.8:
                    mastered_words += 1
                else:
                    learning_words += 1

        average_mastery = total_mastery / total_words if total_words > 0 else 0.0

        return {
            'total_words': total_words,
            'mastered_words': mastered_words,
            'learning_words': learning_words,
            'average_mastery': round(average_mastery * 100, 1)
        }


# 创建全局实例
def get_review_strategy(data_dir):
    """获取复习策略实例"""
    return ReviewStrategy(data_dir)
