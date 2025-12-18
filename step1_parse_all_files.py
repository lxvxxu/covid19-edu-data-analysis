"""
STEP 1: 생활기록부 파싱 (OCR 호환 버전)
========================================
개선사항:
1. OCR 변환 텍스트 파싱 지원 (공백 불규칙 처리)
2. 세특 파싱 패턴 개선
3. 체육/예술 성적 파싱 추가
4. 코로나 기간: 2020.3 ~ 2022.3 (2020~2022년)
5. thefuzz 퍼지 매칭
6. SHA-256 비식별화
"""

import os
import re
import hashlib
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from collections import Counter
import warnings
warnings.filterwarnings('ignore')

# thefuzz 임포트
try:
    from thefuzz import fuzz, process
    FUZZY_AVAILABLE = True
    print("✅ thefuzz 로드 완료")
except ImportError:
    FUZZY_AVAILABLE = False
    print("⚠️  thefuzz 미설치 - 기본 매칭 사용 (pip install thefuzz python-Levenshtein)")


class StudentRecordParser:
    """생활기록부 파서 (OCR 호환 버전)"""
    
    def __init__(self):
        # 교육부 공식 과목 리스트
        self.all_subjects = [
            '국어', '국어Ⅰ', '국어Ⅱ', '국어 I', '국어 II',
            '수학', '수학Ⅰ', '수학Ⅱ', '수학 I', '수학 II',
            '영어', '영어Ⅰ', '영어Ⅱ', '영어 I', '영어 II',
            '화법과 작문', '화법과작문', '독서와 문법', '독서와문법',
            '문학', '독서', '언어와 매체',
            '미적분Ⅰ', '미적분Ⅱ', '미적분 I', '미적분 II', '미적분',
            '확률과 통계', '확률과통계', '기하와 벡터', '기하와벡터', '기하',
            '실용영어Ⅰ', '실용영어Ⅱ', '실용영어 I', '실용영어 II', '실용영어',
            '영어회화', '영어독해와 작문', '영어독해와작문',
            '한국사', '한국지리', '세계지리', '세계사', '동아시아사',
            '경제', '정치와 법', '법과정치', '사회·문화', '사회문화', '사회',
            '생활과 윤리', '윤리와 사상', '윤리와사상',
            '물리학Ⅰ', '물리학Ⅱ', '물리 I', '물리 II', '물리학 I', '물리학 II',
            '화학Ⅰ', '화학Ⅱ', '화학 I', '화학 II', '화학',
            '생명과학Ⅰ', '생명과학Ⅱ', '생명과학 I', '생명과학 II', '생명과학',
            '지구과학Ⅰ', '지구과학Ⅱ', '지구과학 I', '지구과학 II', '지구과학',
            '과학', '융합과학', '과학탐구실험',
            '체육', '운동과 건강', '스포츠 생활', '스포츠문화', '스포츠과학',
            '음악', '음악과생활', '음악과진로', '음악 감상과 비평',
            '미술', '미술창작', '미술 감상과 비평',
            '기술·가정', '기술 . 가정', '기술가정', '정보',
            '한문Ⅰ', '한문Ⅱ', '한문 I', '한문 II', '한문',
            '중국어Ⅰ', '중국어Ⅱ', '중국어 I', '중국어 II',
            '일본어Ⅰ', '일본어Ⅱ', '일본어 I', '일본어 II',
            '독일어Ⅰ', '프랑스어Ⅰ', '스페인어Ⅰ',
            '실용경제', '논술', '진로와 직업', '철학', '심리학', '교육학',
            '고전', '고전읽기',
        ]
        
        # 교과군 매핑
        self.subject_to_group = self._build_subject_group_map()
        
        # 키워드
        self.exploration_keywords = [
            '실험', '실습', '관찰', '측정', '분석', '탐구', '연구', '조사',
            '탐색', '발견', '현장', '답사', '견학', '방문', '체험',
            '프로젝트', '과제연구', '팀프로젝트', '모둠활동',
            '가설', '검증', '실험설계', '데이터', '결과분석', '보고서'
        ]
        
        self.online_keywords = [
            '온라인', '원격', '비대면', '화상', '실시간', '쌍방향',
            'zoom', '줌', '구글클래스룸', 'e-학습터', '이학습터',
            'EBS', 'ebs', '위두랑', '디지털', '인터넷', '원격수업',
            '온라인수업', '화상수업', '동영상', '영상'
        ]
        
        self.qualitative_keywords = [
            '과정', '노력', '태도', '참여', '열정', '몰입', '집중',
            '협력', '협동', '배려', '나눔', '소통', '공감', '존중',
            '성장', '발전', '개선', '극복', '도전', '변화'
        ]
        
        # 성적 등급 매핑
        self.grade_map = {
            'A': 1, 'B': 2, 'C': 3, 'D': 4, 'E': 5,
            '1': 1, '2': 2, '3': 3, '4': 4, '5': 5,
            '6': 6, '7': 7, '8': 8, '9': 9,
            '수': 1, '우': 2, '미': 3, '양': 4, '가': 5,
            'P': 0  # Pass
        }
    
    def _build_subject_group_map(self) -> Dict[str, str]:
        """교과군 매핑"""
        mapping = {}
        for subject in self.all_subjects:
            subj_lower = subject.lower()
            if any(kw in subject for kw in ['국어', '화법', '작문', '독서', '언어', '문학', '고전']):
                mapping[subject] = '국어'
            elif any(kw in subject for kw in ['수학', '미적분', '확률', '통계', '기하']):
                mapping[subject] = '수학'
            elif any(kw in subject for kw in ['영어', 'English']):
                mapping[subject] = '영어'
            elif any(kw in subject for kw in ['역사', '한국사', '세계사', '동아시아', '지리', '경제', '정치', '법', '사회', '윤리']):
                mapping[subject] = '사회'
            elif any(kw in subject for kw in ['과학', '물리', '화학', '생명', '지구', '융합']):
                mapping[subject] = '과학'
            elif any(kw in subject for kw in ['체육', '운동', '스포츠']):
                mapping[subject] = '체육'
            elif any(kw in subject for kw in ['음악', '미술', '연극', '예술']):
                mapping[subject] = '예술'
            elif any(kw in subject for kw in ['기술', '가정', '정보']):
                mapping[subject] = '기술가정'
            elif any(kw in subject for kw in ['독일어', '프랑스어', '스페인어', '중국어', '일본어', '한문']):
                mapping[subject] = '제2외국어'
            else:
                mapping[subject] = '교양'
        return mapping
    
    @staticmethod
    def generate_anonymous_id(name: str, student_id: str) -> str:
        """SHA-256 비식별화"""
        combined = f"{name}_{student_id}"
        return hashlib.sha256(combined.encode('utf-8')).hexdigest()[:16]
    
    def fuzzy_match_subject(self, query: str, threshold: int = 70) -> Tuple[Optional[str], int]:
        """퍼지 매칭"""
        if not query or len(query) < 2:
            return None, 0
        
        # 정확 매칭
        if query in self.all_subjects:
            return query, 100
        
        # 공백/특수문자 제거 후 매칭
        cleaned = re.sub(r'[\s./]+', '', query)
        for subject in self.all_subjects:
            cleaned_subj = re.sub(r'[\s./]+', '', subject)
            if cleaned == cleaned_subj:
                return subject, 100
        
        # thefuzz 퍼지 매칭
        if FUZZY_AVAILABLE:
            result = process.extractOne(query, self.all_subjects, scorer=fuzz.token_sort_ratio)
            if result and result[1] >= threshold:
                return result[0], result[1]
        
        # 부분 매칭
        for subject in self.all_subjects:
            if query in subject or subject in query:
                return subject, 80
        
        return query, 50  # 매칭 실패해도 원본 반환
    
    def extract_years_from_text(self, text: str) -> List[int]:
        """연도 추출"""
        patterns = [
            r'(20\d{2})[\.,\-/]\s*\d{1,2}[\.,\-/]\s*\d{1,2}',
            r'\((20\d{2})\)',
            r'(20\d{2})년',
            r'(20\d{2})학년',
        ]
        
        all_years = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                try:
                    year = int(match)
                    if 2010 <= year <= 2025:
                        all_years.append(year)
                except:
                    pass
        return all_years
    
    def estimate_grade_years(self, text: str, filename: str) -> Dict[int, int]:
        """학년별 연도 추정"""
        grade_years = {}
        
        # 수상경력에서 패턴 찾기
        patterns = [
            r'(20\d{2})[\./\-]\d{1,2}[\./\-]\d{1,2}.*?(\d)학년',
            r'(\d)학년.*?(20\d{2})',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                try:
                    if match[0].isdigit() and len(match[0]) == 4:
                        year, grade = int(match[0]), int(match[1])
                    else:
                        grade, year = int(match[0]), int(match[1])
                    if 1 <= grade <= 3 and 2010 <= year <= 2025:
                        if grade not in grade_years:
                            grade_years[grade] = year
                except:
                    pass
        
        # 연도만 추출해서 추정
        if not grade_years:
            all_years = self.extract_years_from_text(text)
            if all_years:
                year_counts = Counter(all_years)
                common_years = sorted(year_counts.keys())
                if len(common_years) >= 1:
                    base_year = min(common_years)
                    for i, grade in enumerate([1, 2, 3]):
                        grade_years[grade] = base_year + i
        
        return grade_years
    
    def parse_student_info(self, text: str, filename: str) -> Dict:
        """학생 기본 정보 파싱"""
        # 파일명에서 정보 추출
        parts = filename.replace('.txt', '').split('_')
        
        student_id = parts[0] if parts else "unknown"
        grade_level = re.search(r'(\d)학년', filename)
        grade_level = int(grade_level.group(1)) if grade_level else 0
        major = parts[2] if len(parts) > 2 else "unknown"
        name = parts[3] if len(parts) > 3 else "unknown"
        admission = parts[4] if len(parts) > 4 else "unknown"
        
        # 비식별화 ID
        anonymous_id = self.generate_anonymous_id(name, student_id)
        
        # 학년별 연도 추정
        grade_years = self.estimate_grade_years(text, filename)
        
        # 코로나 여부 판단 (2020년 3월 ~ 2022년 3월 = 2020~2022년)
        grade1_covid = 1 if grade_years.get(1) and 2020 <= grade_years[1] <= 2022 else 0
        grade2_covid = 1 if grade_years.get(2) and 2020 <= grade_years[2] <= 2022 else 0
        grade3_covid = 1 if grade_years.get(3) and 2020 <= grade_years[3] <= 2022 else 0
        
        # 코로나 강도 (0~3)
        covid_intensity = grade1_covid + grade2_covid + grade3_covid
        any_covid = 1 if covid_intensity > 0 else 0
        
        return {
            'student_id': anonymous_id,
            'anonymous_id': anonymous_id,
            'original_id': student_id,
            'name_hash': hashlib.sha256(name.encode()).hexdigest()[:8],
            'major': major,
            'admission_type': admission,
            'current_grade': grade_level,
            
            # 학년별 연도
            'grade_year_1': grade_years.get(1),
            'grade_year_2': grade_years.get(2),
            'grade_year_3': grade_years.get(3),
            'grade1_year': grade_years.get(1),
            'grade2_year': grade_years.get(2),
            'grade3_year': grade_years.get(3),
            'hs_graduation_year': grade_years.get(3) + 1 if grade_years.get(3) else None,
            'graduation_year': grade_years.get(3) + 1 if grade_years.get(3) else None,
            
            # 코로나 관련
            'grade1_covid': grade1_covid,
            'grade2_covid': grade2_covid,
            'grade3_covid': grade3_covid,
            'covid_intensity': covid_intensity,
            'any_covid': any_covid,
            'has_covid': any_covid,
            'has_covid_period': any_covid,
            'covid_period': any_covid,
            
            # 재수 여부
            'is_repeat': 0,
        }
    
    def extract_grades(self, text: str, student_id: str, grade_years: Dict) -> List[Dict]:
        """성적 데이터 추출 (OCR 호환)"""
        grades = []
        
        # OCR 텍스트 정리 (불필요한 공백 제거)
        cleaned_text = re.sub(r'\s+', ' ', text)
        
        # 학년별 섹션 분리
        grade_sections = re.split(r'\[(\d)학년\]', cleaned_text)
        
        # 일반 과목 성적 패턴 (OCR 호환)
        # 패턴: 교과 과목 단위수 원점수/평균(표준편차) 성취도(수강자수) [석차등급]
        patterns = [
            # 표준 패턴
            r'([가-힣A-Za-z\s./ⅠⅡ]+?)\s+(\d+)\s+(\d+)\s*/\s*(\d+\.?\s*\d*)\s*\(\s*(\d+\.?\s*\d*)\s*\)\s+([A-EP])\s*\(\s*(\d+)\s*\)\s*(\d)?',
            # 간단 패턴
            r'([가-힣]+)\s+([가-힣A-Za-zⅠⅡ\s]+?)\s+(\d+)\s+(\d+)\s*/\s*(\d+\.?\d*)\s*\((\d+\.?\d*)\)\s+([A-EP])\s*\((\d+)\)',
        ]
        
        for i in range(1, len(grade_sections), 2):
            try:
                grade_year = int(grade_sections[i])
                section_text = grade_sections[i + 1] if i + 1 < len(grade_sections) else ""
                year = grade_years.get(grade_year)
                
                for pattern in patterns:
                    for match in re.finditer(pattern, section_text):
                        try:
                            groups = match.groups()
                            subject_raw = groups[0].strip() if len(groups[0]) > 1 else groups[1].strip() if len(groups) > 1 else ""
                            
                            # 숫자 정리 (OCR 오류 수정)
                            def clean_num(s):
                                return float(re.sub(r'\s+', '', str(s)))
                            
                            subject_matched, score = self.fuzzy_match_subject(subject_raw)
                            subject = subject_matched if subject_matched else subject_raw
                            
                            # 성취도 찾기
                            achievement = None
                            for g in groups:
                                if g and g in 'ABCDEP':
                                    achievement = g
                                    break
                            
                            if not achievement:
                                continue
                            
                            grade_numeric = self.grade_map.get(achievement, 3)
                            grade_type = 'achievement' if achievement in 'ABCDEP' else 'rank'
                            
                            grades.append({
                                'student_id': student_id,
                                'grade_year': grade_year,
                                'year': year,
                                'term': 1,
                                'subject': subject,
                                'subject_raw': subject_raw,
                                'subject_group': self.subject_to_group.get(subject, '교양'),
                                'achievement': achievement,
                                'grade_numeric': grade_numeric,
                                'grade_type': grade_type,
                                'match_score': score,
                            })
                        except:
                            pass
            except:
                pass
        
        # 체육/예술 성적 파싱
        pe_art_pattern = r'<\s*체육\s*[.·]\s*예술.*?>'
        pe_art_sections = re.split(pe_art_pattern, cleaned_text)
        
        # 체육/예술 패턴: 교과 과목 단위수 성취도 단위수 성취도
        pe_pattern = r'(체육|예술[^가-힣]*)\s+([가-힣A-Za-z\s]+?)\s+(\d+)\s+([A-EP])\s+(\d+)\s+([A-EP])'
        
        for section in pe_art_sections[1:] if len(pe_art_sections) > 1 else [cleaned_text]:
            for match in re.finditer(pe_pattern, section):
                try:
                    subject_group = match.group(1).strip()
                    subject = match.group(2).strip()
                    
                    # 1학기
                    achievement1 = match.group(4)
                    grades.append({
                        'student_id': student_id,
                        'grade_year': 1,
                        'term': 1,
                        'subject': subject,
                        'subject_raw': subject,
                        'subject_group': '체육' if '체육' in subject_group else '예술',
                        'achievement': achievement1,
                        'grade_numeric': self.grade_map.get(achievement1, 1),
                        'grade_type': 'achievement',
                    })
                    
                    # 2학기
                    achievement2 = match.group(6)
                    grades.append({
                        'student_id': student_id,
                        'grade_year': 1,
                        'term': 2,
                        'subject': subject,
                        'subject_raw': subject,
                        'subject_group': '체육' if '체육' in subject_group else '예술',
                        'achievement': achievement2,
                        'grade_numeric': self.grade_map.get(achievement2, 1),
                        'grade_type': 'achievement',
                    })
                except:
                    pass
        
        return grades
    
    def extract_seteuk(self, text: str, student_id: str, grade_years: Dict) -> List[Dict]:
        """세특 데이터 추출 (OCR 호환)"""
        seteuk_list = []
        
        # OCR 텍스트 정리
        cleaned_text = text.replace('\n', ' ')
        
        # 세특 섹션 찾기 (OCR 변환된 형태 포함)
        seteuk_patterns = [
            r'세\s*부\s*능\s*력\s*및\s*특\s*기\s*사\s*항',
            r'세부\s*능력\s*및\s*특기사항',
            r'세부능력특기사항',
            r'세부능력\s*및\s*특기\s*사항',
        ]
        
        seteuk_start = None
        for pattern in seteuk_patterns:
            match = re.search(pattern, cleaned_text)
            if match:
                seteuk_start = match.end()
                break
        
        if seteuk_start is None:
            return seteuk_list
        
        # 세특 끝 찾기
        end_patterns = [r'\d+\.\s*[가-힣]+', r'<\s*체육', r'\[\d학년\]']
        seteuk_end = len(cleaned_text)
        for pattern in end_patterns:
            match = re.search(pattern, cleaned_text[seteuk_start:])
            if match:
                seteuk_end = min(seteuk_end, seteuk_start + match.start())
        
        seteuk_text = cleaned_text[seteuk_start:seteuk_end]
        
        # 과목별 세특 추출 (과목명: 내용 형태)
        subject_pattern = r'([가-힣A-Za-zⅠⅡ\s]+?)\s*:\s*(.+?)(?=[가-힣A-Za-zⅠⅡ\s]+?\s*:|$)'
        
        for match in re.finditer(subject_pattern, seteuk_text, re.DOTALL):
            subject = match.group(1).strip()
            content = match.group(2).strip()
            
            # 너무 짧은 내용 제외
            if len(content) < 20:
                continue
            
            # 과목명 정리
            subject = re.sub(r'\s+', ' ', subject)
            subject_matched, _ = self.fuzzy_match_subject(subject)
            if subject_matched:
                subject = subject_matched
            
            # 키워드 빈도
            content_len = len(content)
            exp_count = sum(1 for kw in self.exploration_keywords if kw in content)
            online_count = sum(1 for kw in self.online_keywords if kw in content)
            qual_count = sum(1 for kw in self.qualitative_keywords if kw in content)
            
            seteuk_list.append({
                'student_id': student_id,
                'subject': subject,
                'content_length': content_len,
                'kw_count_exploration': exp_count,
                'kw_count_online': online_count,
                'kw_count_qualitative': qual_count,
                'kw_freq_exploration': exp_count / content_len * 1000 if content_len > 0 else 0,
                'kw_freq_online': online_count / content_len * 1000 if content_len > 0 else 0,
                'kw_freq_qualitative': qual_count / content_len * 1000 if content_len > 0 else 0,
            })
        
        return seteuk_list
    
    def calculate_volatility(self, grades: List[Dict], student_id: str) -> Dict:
        """성적 변동성 계산"""
        result = {'student_id': student_id}
        
        if not grades:
            result['overall_volatility'] = 0
            result['overall_mean'] = 0
            result['overall_count'] = 0
            return result
        
        df = pd.DataFrame(grades)
        
        # 전체 변동성
        if 'grade_numeric' in df.columns and len(df) > 0:
            valid = df['grade_numeric'].dropna()
            result['overall_volatility'] = valid.std() if len(valid) > 1 else 0
            result['overall_mean'] = valid.mean() if len(valid) > 0 else 0
            result['overall_count'] = len(valid)
        
        # 학년별 변동성
        for grade in [1, 2, 3]:
            grade_df = df[df['grade_year'] == grade] if 'grade_year' in df.columns else pd.DataFrame()
            if len(grade_df) >= 2 and 'grade_numeric' in grade_df.columns:
                valid = grade_df['grade_numeric'].dropna()
                result[f'grade{grade}_volatility'] = valid.std() if len(valid) > 1 else 0
                result[f'grade{grade}_mean'] = valid.mean()
                result[f'grade{grade}_count'] = len(valid)
            else:
                result[f'grade{grade}_volatility'] = 0
                result[f'grade{grade}_mean'] = 0
                result[f'grade{grade}_count'] = 0
        
        return result


def create_yearly_covid_data(df_students: pd.DataFrame) -> pd.DataFrame:
    """yearly_covid.csv 생성"""
    yearly_data = []
    
    for _, student in df_students.iterrows():
        student_id = student.get('anonymous_id', student.get('student_id'))
        
        for grade in [1, 2, 3]:
            year = student.get(f'grade_year_{grade}')
            covid = student.get(f'grade{grade}_covid', 0)
            
            if pd.notna(year) and year is not None:
                yearly_data.append({
                    'anonymous_id': student_id,
                    'student_id': student_id,
                    'grade': grade,
                    'year': int(year),
                    'is_covid_period': int(covid) if pd.notna(covid) else 0,
                })
    
    return pd.DataFrame(yearly_data)


def create_keywords_data(df_seteuk: pd.DataFrame) -> pd.DataFrame:
    """keywords.csv 생성"""
    if df_seteuk.empty:
        return pd.DataFrame()
    
    keywords = df_seteuk.groupby('student_id').agg({
        'kw_count_exploration': 'sum',
        'kw_count_online': 'sum',
        'kw_count_qualitative': 'sum',
    }).reset_index()
    
    keywords.columns = ['anonymous_id', 'exploration_total', 'remote_total', 'qualitative_total']
    return keywords


def main():
    """메인 함수"""
    print("\n" + "="*80)
    print("STEP 1: 생활기록부 파싱 (OCR 호환 버전)")
    print("="*80)
    
    parser = StudentRecordParser()
    
    # 데이터 디렉토리
    raw_dir = Path('data/raw')
    processed_dir = Path('data/processed')
    processed_dir.mkdir(parents=True, exist_ok=True)
    
    # txt 파일 찾기
    txt_files = list(raw_dir.glob('*.txt'))
    print(f"\n총 {len(txt_files)}개 파일 발견")
    
    if not txt_files:
        print("⚠️  data/raw/ 디렉토리에 txt 파일이 없습니다!")
        return
    
    # 데이터 저장
    all_students = []
    all_grades = []
    all_seteuk = []
    all_volatility = []
    
    print("\n파싱 진행 중...")
    for i, filepath in enumerate(txt_files, 1):
        print(f"  [{i}/{len(txt_files)}] {filepath.name}...", end=' ')
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                text = f.read()
        except:
            try:
                with open(filepath, 'r', encoding='cp949') as f:
                    text = f.read()
            except:
                print("❌ 인코딩 오류")
                continue
        
        try:
            # 학생 정보
            student_info = parser.parse_student_info(text, filepath.name)
            student_id = student_info['anonymous_id']
            grade_years = {
                1: student_info.get('grade_year_1'),
                2: student_info.get('grade_year_2'),
                3: student_info.get('grade_year_3'),
            }
            
            # 성적
            grades = parser.extract_grades(text, student_id, grade_years)
            
            # 세특
            seteuk = parser.extract_seteuk(text, student_id, grade_years)
            
            # 변동성
            volatility = parser.calculate_volatility(grades, student_id)
            
            all_students.append(student_info)
            all_grades.extend(grades)
            all_seteuk.extend(seteuk)
            all_volatility.append(volatility)
            
            print(f"✓ (성적:{len(grades)}, 세특:{len(seteuk)})")
        except Exception as e:
            print(f"❌ {e}")
    
    # DataFrame 생성
    df_students = pd.DataFrame(all_students)
    df_grades = pd.DataFrame(all_grades)
    df_seteuk = pd.DataFrame(all_seteuk)
    df_volatility = pd.DataFrame(all_volatility)
    df_yearly_covid = create_yearly_covid_data(df_students)
    df_keywords = create_keywords_data(df_seteuk)
    
    # 저장
    print("\n💾 데이터 저장 중...")
    
    files_to_save = {
        'student_info.csv': df_students,
        'students_anonymized.csv': df_students,
        'grades.csv': df_grades,
        'seteuk.csv': df_seteuk,
        'volatility.csv': df_volatility,
        'yearly_covid.csv': df_yearly_covid,
        'keywords.csv': df_keywords,
    }
    
    for filename, dataframe in files_to_save.items():
        try:
            dataframe.to_csv(processed_dir / filename, index=False, encoding='utf-8-sig')
            print(f"  ✓ {filename} ({len(dataframe)} rows)")
        except Exception as e:
            print(f"  ❌ {filename}: {e}")
    
    # 요약
    print("\n" + "="*80)
    print("✅ 파싱 완료!")
    print("="*80)
    print(f"\n📊 학생 수: {len(df_students)}명")
    print(f"📊 성적 레코드: {len(df_grades)}건")
    print(f"📊 세특 레코드: {len(df_seteuk)}건")
    
    if 'covid_intensity' in df_students.columns:
        print(f"\n📊 코로나 영향 강도 분포 (영향받은 학년 수):")
        for intensity in sorted(df_students['covid_intensity'].unique()):
            count = (df_students['covid_intensity'] == intensity).sum()
            label = "미경험" if intensity == 0 else f"{int(intensity)}개 학년"
            print(f"   - {label}: {count}명")
    
    if 'any_covid' in df_students.columns:
        covid_count = df_students['any_covid'].sum()
        print(f"\n📊 코로나 경험:")
        print(f"   - 있음: {covid_count}명")
        print(f"   - 없음: {len(df_students) - covid_count}명")


if __name__ == "__main__":
    main()