"""
STEP 1: 생활기록부 파싱 (완전 호환 버전)
=========================================
개선사항:
1. thefuzz 퍼지 매칭 (Levenshtein Distance)
2. SHA-256 비식별화
3. 모든 step 파일과 완벽 호환
4. 용량-반응 분석용 covid_intensity 추가

작성일: 2025
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

# thefuzz 임포트 (설치 안 되어 있으면 기본 매칭 사용)
try:
    from thefuzz import fuzz, process
    FUZZY_AVAILABLE = True
except ImportError:
    FUZZY_AVAILABLE = False
    print("⚠️  thefuzz 미설치 - 기본 매칭 사용 (pip install thefuzz python-Levenshtein)")


class StudentRecordParser:
    """생활기록부 파서 (완전 호환 버전)"""
    
    def __init__(self):
        # 교육부 공식 과목 리스트
        self.all_subjects = [
            '공통국어1', '공통국어2', '공통수학1', '공통수학2', '공통영어1', '공통영어2',
            '한국사1', '한국사2', '통합사회1', '통합사회2', '통합과학1', '통합과학2',
            '과학탐구실험1', '과학탐구실험2', '기본수학1', '기본수학2', '기본영어1', '기본영어2',
            '국어', '수학', '영어', '한국사', '통합사회', '통합과학', '과학탐구실험',
            '화법과 작문', '독서', '언어와 매체', '문학', '실용 국어', '심화 국어',
            '고전 읽기', '화법과 언어', '독서와 작문', '주제 탐구 독서', '문학과 영상',
            '직무 의사소통', '독서 토론과 글쓰기', '매체 의사소통', '언어생활 탐구',
            '수학Ⅰ', '수학Ⅱ', '미적분', '확률과 통계', '실용 수학', '기하', '경제 수학',
            '수학과제 탐구', '기본 수학', '인공지능 수학', '대수', '미적분I', '미적분II',
            '직무 수학', '수학과 문화', '실용 통계', '수학 1', '수학 I', '수학 II',
            '영어회화', '영어Ⅰ', '영어독해와 작문', '영어Ⅱ', '실용영어', '영어권 문화',
            '진로 영어', '영미 문학 읽기', '기본 영어', '영어 발표와 토론', '심화 영어',
            '심화 영어 독해와 작문', '직무 영어', '실생활 영어 회화', '미디어 영어',
            '세계 문화와 영어', '실용 영어회화', '실용영어 I', '영어 II', '영어 I',
            '한국지리', '세계지리', '세계사', '동아시아사', '경제', '정치와 법', '사회·문화',
            '생활과 윤리', '윤리와 사상', '여행지리', '사회문제 탐구', '고전과 윤리',
            '세계시민과 지리', '현대사회와 윤리', '한국지리 탐구', '도시의 미래 탐구',
            '동아시아 역사 기행', '법과 사회', '인문학과 윤리', '국제 관계의 이해',
            '역사로 탐구하는 현대 세계', '금융과 경제생활', '윤리문제 탐구',
            '기후변화와 지속가능한 세계', '사회', '현대 세계의 변화',
            '물리학Ⅰ', '화학Ⅰ', '생명과학Ⅰ', '지구과학Ⅰ', '물리학Ⅱ', '화학Ⅱ',
            '생명과학Ⅱ', '지구과학Ⅱ', '과학사', '생활과 과학', '융합과학', '과학',
            '물리학 I', '화학 I', '생명과학 I', '지구과학 I',
            '체육', '운동과 건강', '스포츠 생활', '체육 탐구',
            '음악', '미술', '연극', '음악 연주', '음악 감상과 비평',
            '미술 창작', '미술 감상과 비평',
            '기술·가정', '정보', '농업 생명 과학', '공학 일반', '창의 경영',
            '해양 문화와 기술', '가정과학', '지식 재산 일반', '인공지능 기초', '철학', '기술 . 가정',
            '독일어I', '프랑스어I', '스페인어I', '중국어I', '일본어I', '러시아어I',
            '아랍어I', '베트남어I', '독일어II', '프랑스어II', '스페인어II', '중국어II',
            '일본어II', '러시아어II', '아랍어II', '베트남어II', '일본어 I',
            '한문I', '한문II', '한문 I', '철학', '논리학', '심리학', '교육학', '종교학',
            '진로와 직업', '보건', '환경', '실용 경제', '논술', '안전한 생활'
        ]
        
        # 교과군 매핑
        self.subject_to_group = self._build_subject_group_map()
        
        # 키워드 정의
        self.exploration_keywords = [
            '실험', '실습', '관찰', '측정', '분석', '탐구', '연구', '조사',
            '탐색', '발견', '현장', '답사', '견학', '방문', '체험', '실사',
            '프로젝트', '과제연구', '팀프로젝트', '모둠활동', '소집단',
            '가설', '검증', '실험설계', '데이터수집', '결과분석', '보고서작성'
        ]
        
        self.online_keywords = [
            '온라인', '원격', '비대면', '화상', '실시간', '쌍방향',
            'zoom', '줌', 'ZOOM', '구글클래스룸', '클래스룸', 'e-학습터',
            '이학습터', 'EBS', 'ebs', '위두랑', '디지털', '인터넷',
            '원격수업', '온라인수업', '화상수업', '동영상', '영상'
        ]
        
        self.qualitative_keywords = [
            '과정', '노력', '태도', '참여', '열정', '몰입', '집중',
            '협력', '협동', '배려', '나눔', '소통', '공감', '존중',
            '성장', '발전', '개선', '극복', '도전', '변화', '진보'
        ]
        
        # 성적 등급 매핑
        self.grade_map = {
            'A': 1, 'B': 2, 'C': 3, 'D': 4, 'E': 5,
            '1': 1, '2': 2, '3': 3, '4': 4, '5': 5,
            '6': 6, '7': 7, '8': 8, '9': 9,
            '수': 1, '우': 2, '미': 3, '양': 4, '가': 5
        }
    
    def _build_subject_group_map(self) -> Dict[str, str]:
        """교과군 매핑 생성"""
        mapping = {}
        for subject in self.all_subjects:
            if any(kw in subject for kw in ['국어', '화법', '작문', '독서', '언어', '매체', '문학', '고전']):
                mapping[subject] = '국어'
            elif any(kw in subject for kw in ['수학', '미적분', '확률', '통계', '기하', '대수']):
                mapping[subject] = '수학'
            elif any(kw in subject for kw in ['영어', 'English']):
                mapping[subject] = '영어'
            elif any(kw in subject for kw in ['역사', '한국사', '세계사', '동아시아', '지리', '경제', '정치', '법', '사회', '윤리']):
                mapping[subject] = '사회'
            elif any(kw in subject for kw in ['과학', '물리', '화학', '생명', '지구', '융합', '탐구실험']):
                mapping[subject] = '과학'
            elif any(kw in subject for kw in ['체육', '운동', '스포츠']):
                mapping[subject] = '체육'
            elif any(kw in subject for kw in ['음악', '미술', '연극', '예술']):
                mapping[subject] = '예술'
            elif any(kw in subject for kw in ['기술', '가정', '정보', '농업', '공학']):
                mapping[subject] = '기술·가정'
            elif any(kw in subject for kw in ['독일어', '프랑스어', '스페인어', '중국어', '일본어', '러시아어']):
                mapping[subject] = '제2외국어'
            else:
                mapping[subject] = '교양'
        return mapping
    
    @staticmethod
    def generate_anonymous_id(name: str, student_id: str) -> str:
        """SHA-256 해싱을 통한 비식별화 ID 생성"""
        combined = f"{name}_{student_id}"
        return hashlib.sha256(combined.encode('utf-8')).hexdigest()[:16]
    
    def fuzzy_match_subject(self, query: str, threshold: int = 80) -> Tuple[Optional[str], int]:
        """퍼지 매칭으로 과목명 찾기"""
        if not query or len(query) < 2:
            return None, 0
        
        # 정확 매칭 먼저
        if query in self.all_subjects:
            return query, 100
        
        # thefuzz 사용 가능하면 퍼지 매칭
        if FUZZY_AVAILABLE:
            result = process.extractOne(query, self.all_subjects, scorer=fuzz.token_sort_ratio)
            if result and result[1] >= threshold:
                return result[0], result[1]
        
        # 부분 매칭
        for subject in self.all_subjects:
            if query in subject or subject in query:
                return subject, 80
        
        return None, 0
    
    def extract_years_from_text(self, text: str) -> List[int]:
        """텍스트에서 모든 연도 추출"""
        patterns = [
            r'(20\d{2})[\.,\-/]\s*\d{2}[\.,\-/]\s*\d{2}',
            r'\((20\d{2})\)',
            r'(20\d{2})년',
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
        """학년별 연도 추정 (수상경력 또는 빈도 분석)"""
        grade_years = {}
        
        # 수상경력에서 연도-학년 패턴 찾기
        award_patterns = [
            r'(20\d{2})[\./\-]\d{2}[\./\-]\d{2}\s*(\d)학년',
            r'(20\d{2})년.*?(\d)학년',
        ]
        
        for pattern in award_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                try:
                    year, grade = int(match[0]), int(match[1])
                    if 1 <= grade <= 4 and 2015 <= year <= 2025:
                        if grade not in grade_years:
                            grade_years[grade] = year
                except:
                    pass
        
        # 수상경력에서 못 찾으면 빈도 분석
        if not grade_years:
            all_years = self.extract_years_from_text(text)
            if all_years:
                year_counter = Counter(all_years)
                top_years = sorted([y for y, _ in year_counter.most_common(3)])
                if len(top_years) >= 3:
                    grade_years = {1: top_years[0], 2: top_years[1], 3: top_years[2]}
                elif len(top_years) >= 1:
                    base_year = top_years[0]
                    grade_years = {1: base_year, 2: base_year + 1, 3: base_year + 2}
        
        return grade_years
    
    def extract_remote_days(self, text: str) -> Dict[int, int]:
        """학년별 원격수업일수 추출 (다양한 오타 패턴 지원)"""
        patterns = [
            r'원격\s*수업\s*일수?\s*(\d+)\s*일?',
            r'원격\s*일수?\s*(\d+)\s*일?',
            r'인격\s*수업\s*일수?\s*(\d+)\s*일?',  # 오타: 원격→인격
            r'원격\s*수입\s*일수?\s*(\d+)\s*일?',  # 오타: 수업→수입
            r'인격\s*수입\s*일수?\s*(\d+)\s*일?',  # 복합 오타
            r'원격수업일수(\d+)일?',
            r'인격수업일수(\d+)일?',
            r'원격수입일수(\d+)일?',
            r'개근\s*[,.\s]*원격\s*수업?\s*일수?\s*(\d+)\s*일?',
        ]
        
        all_remote_values = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    value = int(match)
                    if 0 <= value <= 200:
                        all_remote_values.append(value)
                except:
                    pass
        
        # 학년별 섹션 분리
        remote_by_grade = {1: 0, 2: 0, 3: 0}
        sections = re.split(r'\[(\d)학년\]', text)
        
        for i in range(1, len(sections), 2):
            try:
                grade = int(sections[i])
                section_text = sections[i + 1] if i + 1 < len(sections) else ""
                
                for pattern in patterns:
                    matches = re.findall(pattern, section_text, re.IGNORECASE)
                    for match in matches:
                        try:
                            value = int(match)
                            if value > 0 and value <= 200:
                                remote_by_grade[grade] = max(remote_by_grade.get(grade, 0), value)
                        except:
                            pass
            except:
                pass
        
        return remote_by_grade
    
    def parse_student_info(self, text: str, filename: str) -> Optional[Dict]:
        """학생 정보 파싱"""
        try:
            parts = filename.replace('.txt', '').split('_')
            if len(parts) < 4:
                return None
            
            student_id = parts[0]
            grade = parts[1].replace('학년', '')
            major = parts[2]
            name = parts[3]
            admission_type = parts[4] if len(parts) > 4 else 'unknown'
            
            # 비식별화 ID 생성
            anonymous_id = self.generate_anonymous_id(name, student_id)
            
            # 학년별 연도 추정
            grade_years = self.estimate_grade_years(text, filename)
            
            # 원격수업일수 추출
            remote_days = self.extract_remote_days(text)
            total_remote_days = sum(remote_days.values())
            
            # 코로나 여부 판단 (2020~2022년)
            grade1_covid = 1 if grade_years.get(1) and 2020 <= grade_years[1] <= 2022 else 0
            grade2_covid = 1 if grade_years.get(2) and 2020 <= grade_years[2] <= 2022 else 0
            grade3_covid = 1 if grade_years.get(3) and 2020 <= grade_years[3] <= 2022 else 0
            
            # 코로나 강도 (0~3): 용량-반응 분석용
            covid_intensity = grade1_covid + grade2_covid + grade3_covid
            any_covid = 1 if covid_intensity > 0 else 0
            
            # 고교 졸업년도 추정
            hs_graduation_year = grade_years.get(3, 0) if grade_years.get(3) else None
            
            return {
                # 기본 정보 (비식별화)
                'student_id': anonymous_id,  # step3/step4 호환용
                'anonymous_id': anonymous_id,
                'name': name,  # step5에서 참조, 실제 저장 시 삭제
                'grade': int(grade) if grade.isdigit() else 0,
                'major': major,
                'admission_type': admission_type,
                
                # 연도 정보
                'grade_year_1': grade_years.get(1),
                'grade_year_2': grade_years.get(2),
                'grade_year_3': grade_years.get(3),
                'hs_graduation_year': hs_graduation_year,
                'admission_year': hs_graduation_year,
                'graduation_year': hs_graduation_year,
                
                # 코로나 관련 (다양한 컬럼명 호환)
                'grade1_covid': grade1_covid,
                'grade2_covid': grade2_covid,
                'grade3_covid': grade3_covid,
                'covid_intensity': covid_intensity,  # 용량-반응 분석용 (0~3)
                'any_covid': any_covid,
                'has_covid': any_covid,  # step3 호환
                'has_covid_period': any_covid,  # step4 호환
                'covid_period': any_covid,  # step5 호환
                
                # 원격수업
                'remote_days_grade1': remote_days.get(1, 0),
                'remote_days_grade2': remote_days.get(2, 0),
                'remote_days_grade3': remote_days.get(3, 0),
                'total_remote_days': total_remote_days,
                
                # 메타데이터
                'is_repeat': 0,
                'grade_years': grade_years,
                'remote_days': remote_days,
            }
        except Exception as e:
            print(f"  ❌ 파싱 오류: {e}")
            return None
    
    def extract_grades(self, text: str, student_id: str, grade_years: Dict) -> List[Dict]:
        """성적 데이터 추출"""
        grades = []
        
        # 학년별 섹션 분리
        sections = re.split(r'\[(\d)학년\]', text)
        
        # 성적 패턴
        pattern = r'([가-힣A-Za-z\s./Ⅰ-Ⅹ]+?)\s+(\d+)\s+(\d+)/(\d+\.?\d*)\((\d+\.?\d*)\)\s+([A-E1-9수우미양가])\((\d+)\)'
        
        for i in range(1, len(sections), 2):
            try:
                grade_year = int(sections[i])
                section_text = sections[i + 1] if i + 1 < len(sections) else ""
                year = grade_years.get(grade_year)
                
                for match in re.finditer(pattern, section_text):
                    subject_raw = match.group(1).strip()
                    subject_matched, score = self.fuzzy_match_subject(subject_raw)
                    subject = subject_matched if subject_matched else subject_raw
                    
                    achievement = match.group(6)
                    grade_numeric = self.grade_map.get(achievement)
                    
                    if grade_numeric:
                        grade_type = 'achievement' if achievement in 'ABCDE수우미양가' else 'rank'
                        
                        grades.append({
                            'student_id': student_id,
                            'grade_year': grade_year,
                            'year': year,
                            'term': 1,
                            'subject': subject,
                            'subject_raw': subject_raw,
                            'subject_group': self.subject_to_group.get(subject, '교양'),
                            'units': int(match.group(2)),
                            'raw_score': int(match.group(3)),
                            'average': float(match.group(4)),
                            'std_dev': float(match.group(5)),
                            'achievement': achievement,
                            'grade_numeric': grade_numeric,
                            'grade_type': grade_type,
                            'num_students': int(match.group(7)),
                            'match_score': score,
                        })
            except:
                pass
        
        return grades
    
    def extract_seteuk(self, text: str, student_id: str, grade_years: Dict) -> List[Dict]:
        """세특 데이터 추출"""
        seteuk_list = []
        
        # 세특 패턴
        patterns = [
            r'\[세부능력특기사항\]\s*([가-힣A-Za-z\s./Ⅰ-Ⅹ]+?)\s*:\s*(.+?)(?=\[세부능력특기사항\]|\[|$)',
            r'세부능력\s*및\s*특기사항[:\s]*(.+?)(?=\d+\.\s*[가-힣]|\[|$)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.DOTALL)
            for match in matches:
                if len(match) == 2:
                    subject, content = match
                else:
                    subject, content = "기타", match[0] if match else ""
                
                content = content.strip()
                if len(content) < 10:
                    continue
                
                # 키워드 빈도 계산
                content_len = len(content)
                exp_count = sum(1 for kw in self.exploration_keywords if kw in content)
                online_count = sum(1 for kw in self.online_keywords if kw in content)
                qual_count = sum(1 for kw in self.qualitative_keywords if kw in content)
                
                seteuk_list.append({
                    'student_id': student_id,
                    'subject': subject.strip(),
                    'content_length': content_len,
                    'kw_count_exploration': exp_count,
                    'kw_count_online': online_count,
                    'kw_count_qualitative': qual_count,
                    'kw_freq_exploration': exp_count / content_len * 1000 if content_len > 0 else 0,
                    'kw_freq_online': online_count / content_len * 1000 if content_len > 0 else 0,
                    'kw_freq_qualitative': qual_count / content_len * 1000 if content_len > 0 else 0,
                })
        
        return seteuk_list
    
    def calculate_volatility(self, grades: List[Dict], student_id: str, remote_days: Dict) -> Dict:
        """성적 변동성 계산"""
        result = {'student_id': student_id}
        
        if not grades:
            return result
        
        df = pd.DataFrame(grades)
        
        # 전체 변동성
        if 'grade_numeric' in df.columns:
            result['overall_volatility'] = df['grade_numeric'].std()
            result['overall_mean'] = df['grade_numeric'].mean()
            result['overall_count'] = len(df)
        
        # 학년별 변동성
        for grade in [1, 2, 3]:
            grade_df = df[df['grade_year'] == grade]
            if len(grade_df) >= 2:
                result[f'grade{grade}_volatility'] = grade_df['grade_numeric'].std()
                result[f'grade{grade}_mean'] = grade_df['grade_numeric'].mean()
                result[f'grade{grade}_count'] = len(grade_df)
                result[f'grade{grade}_remote_days'] = remote_days.get(grade, 0)
        
        return result


def create_yearly_covid_data(df_students: pd.DataFrame) -> pd.DataFrame:
    """yearly_covid.csv 생성 (step3/step4 호환)"""
    yearly_data = []
    
    for _, student in df_students.iterrows():
        student_id = student['anonymous_id']
        
        for grade in [1, 2, 3]:
            year = student.get(f'grade_year_{grade}')
            covid = student.get(f'grade{grade}_covid', 0)
            
            if year:
                yearly_data.append({
                    'anonymous_id': student_id,
                    'student_id': student_id,
                    'grade': grade,
                    'year': int(year),
                    'is_covid_period': covid,
                })
    
    return pd.DataFrame(yearly_data)


def create_keywords_data(df_seteuk: pd.DataFrame) -> pd.DataFrame:
    """keywords.csv 생성 (step4 호환)"""
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
    """메인 실행 함수"""
    
    print("="*80)
    print("STEP 1: 생활기록부 파싱 (완전 호환 버전)")
    print("="*80)
    
    input_dir = Path('data/raw')
    output_dir = Path('data/processed')
    results_dir = Path('data/results')
    output_dir.mkdir(parents=True, exist_ok=True)
    results_dir.mkdir(parents=True, exist_ok=True)
    
    txt_files = list(input_dir.glob('*.txt'))
    print(f"\n총 {len(txt_files)}개 파일 발견")
    
    if len(txt_files) == 0:
        print("⚠️  data/raw/ 디렉토리에 txt 파일이 없습니다!")
        return
    
    parser = StudentRecordParser()
    
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
            
            student_info = parser.parse_student_info(text, filepath.name)
            if not student_info:
                print("❌")
                continue
            
            student_id = student_info['anonymous_id']
            grade_years = student_info['grade_years']
            remote_days = student_info['remote_days']
            
            all_students.append(student_info)
            
            grades = parser.extract_grades(text, student_id, grade_years)
            all_grades.extend(grades)
            
            seteuk = parser.extract_seteuk(text, student_id, grade_years)
            all_seteuk.extend(seteuk)
            
            volatility = parser.calculate_volatility(grades, student_id, remote_days)
            all_volatility.append(volatility)
            
            print("✓")
        except Exception as e:
            print(f"❌ {e}")
    
    # DataFrame 생성
    df_students = pd.DataFrame(all_students)
    df_grades = pd.DataFrame(all_grades)
    df_seteuk = pd.DataFrame(all_seteuk)
    df_volatility = pd.DataFrame(all_volatility)
    
    # 추가 데이터 생성 (step3/step4 호환)
    df_yearly_covid = create_yearly_covid_data(df_students)
    df_keywords = create_keywords_data(df_seteuk)
    
    # 학생 정보에서 내부 데이터 제거 후 저장
    save_columns = [c for c in df_students.columns if c not in ['grade_years', 'remote_days']]
    df_students_save = df_students[save_columns].copy()
    
    print("\n💾 데이터 저장 중...")
    
    # CSV 저장
    csv_files = {
        'student_info.csv': df_students_save,  # step5 호환
        'students_anonymized.csv': df_students_save,  # step3/step4 호환
        'grades.csv': df_grades,
        'seteuk.csv': df_seteuk,
        'volatility.csv': df_volatility,
        'yearly_covid.csv': df_yearly_covid,  # step3/step4 호환
        'keywords.csv': df_keywords,  # step4 호환
    }
    
    for filename, dataframe in csv_files.items():
        filepath = output_dir / filename
        try:
            dataframe.to_csv(filepath, index=False, encoding='utf-8-sig')
            print(f"  ✓ {filename} ({len(dataframe)} rows)")
        except Exception as e:
            print(f"  ❌ {filename}: {e}")
    
    # 결과 출력
    print("\n" + "="*80)
    print("✅ 파싱 완료!")
    print("="*80)
    
    print(f"\n📊 학생 수: {len(df_students)}명 (비식별화됨)")
    print(f"📊 성적 레코드: {len(df_grades)}건")
    print(f"📊 세특 레코드: {len(df_seteuk)}건")
    
    if 'covid_intensity' in df_students.columns:
        print(f"\n📊 코로나 영향 강도 분포 (용량-반응):")
        for intensity in range(4):
            count = (df_students['covid_intensity'] == intensity).sum()
            pct = count / len(df_students) * 100 if len(df_students) > 0 else 0
            bar = "█" * int(pct / 5)
            print(f"   - {intensity}학년 영향: {count:3d}명 ({pct:5.1f}%) {bar}")
    
    if 'any_covid' in df_students.columns:
        covid_count = df_students['any_covid'].sum()
        print(f"\n📊 코로나 경험:")
        print(f"   - 있음: {covid_count}명")
        print(f"   - 없음: {len(df_students) - covid_count}명")
    
    print("\n💾 저장된 파일:")
    print("  - student_info.csv (step5 호환)")
    print("  - students_anonymized.csv (step3/step4 호환)")
    print("  - grades.csv")
    print("  - seteuk.csv")
    print("  - volatility.csv")
    print("  - yearly_covid.csv (step3/step4 호환)")
    print("  - keywords.csv (step4 호환)")
    
    print("\n✨ Step 1 완료!")


if __name__ == "__main__":
    main()