# COVID-19 대학입시 영향 분석 프로젝트 - 최종 요약

## 📦 제공되는 파일

### 1. 실행 파일 (5개)
- `step1_parse_all_files.py` - 생활기록부 파싱 (69개 파일 → CSV)
- `step2_exploratory_analysis.py` - 탐색적 데이터 분석
- `step3_hypothesis_testing.py` - 가설 검증 (t-test, mediation, regression)
- `step4_visualization.py` - 고품질 시각화 생성
- `step5_generate_reports.py` - 개별/종합 리포트 생성

### 2. 실행 스크립트
- `run_all.sh` - 전체 파이프라인 자동 실행

### 3. 문서
- `README.md` - 프로젝트 개요 및 구조
- `EXECUTION_GUIDE.md` - 상세 실행 가이드

---

## 🎯 프로젝트 목표

**3개 가설 검증**:
1. **H1-1**: COVID 코호트의 성적 변동성 증가
2. **H1-2**: 세특 텍스트 변화(탐구→온라인)의 매개효과
3. **H1-3**: 대학 전형요강의 정성평가 강조 변화

---

## 🚀 사용 방법

### 준비 단계
```bash
# 1. 디렉토리 구조 생성
mkdir -p data/raw data/processed data/results outputs/figures outputs/reports logs

# 2. txt 파일 배치
cp /path/to/69files/*.txt data/raw/

# 3. 패키지 설치
pip install pandas numpy scipy statsmodels matplotlib seaborn tqdm --break-system-packages
```

### 실행 방법

**방법 1: 한 번에 실행 (권장)**
```bash
bash run_all.sh
```

**방법 2: 단계별 실행**
```bash
python step1_parse_all_files.py  # 5-10분
python step2_exploratory_analysis.py  # 2-3분
python step3_hypothesis_testing.py  # 3-5분
python step4_visualization.py  # 2-3분
python step5_generate_reports.py  # 5-10분
```

**총 소요시간**: 약 20-30분 (69개 파일 기준)

---

## 📊 출력 결과물

### 1. 처리된 데이터 (data/processed/)
- `student_info.csv` - 69명 학생 정보
- `grades.csv` - ~1,500-2,000건 성적 데이터
- `seteuk.csv` - ~800-1,000건 세특 데이터
- `volatility.csv` - 69명 변동성 데이터

### 2. 분석 결과 (data/results/)
- `summary_statistics.csv` - 코호트별 요약 통계
- `hypothesis_tests.csv` - 가설 검증 결과

### 3. 시각화 (outputs/figures/)
- `eda/` - 탐색적 분석 그래프 (3개)
- `hypothesis/` - 가설 검증 그래프 (10개+)
  - 변동성 비교 (박스플롯, 바이올린플롯, 트렌드)
  - 키워드 빈도 비교
  - 매개효과 경로 분석
  - 교과군별 분석

### 4. 리포트 (outputs/reports/)
- `individual/` - 개별 학생 리포트 69개
- `comprehensive_report.txt` - 종합 분석 리포트

---

## 🔑 핵심 기능

### 1. 가변 교과목 구조 대응
- 교육과정별로 다른 과목명 자동 인식
- 교과군 자동 분류 (국어, 수학, 영어, 사회, 과학)
- 유연한 패턴 매칭으로 다양한 성적표 형식 처리

### 2. 키워드 자동 추출
**탐구/실험 키워드** (26개):
실험, 실습, 관찰, 측정, 분석, 탐구, 연구, 조사, 프로젝트, 모둠활동, 협력, 협동 등

**온라인/원격 키워드** (22개):
온라인, 원격, 비대면, 화상, zoom, 구글클래스룸, 디지털, 인터넷, EBS 등

### 3. 통계 분석
- **Independent t-test / Welch's t-test**: 코호트 간 평균 차이
- **Levene's test**: 분산 동질성 검정
- **Mediation Analysis**: 매개효과 검증 (Baron & Kenny)
- **OLS Regression**: 패널 회귀분석
- **Effect Size**: Cohen's d 계산

### 4. 고품질 시각화
- 300 DPI 고해상도
- 논문 게재 가능 품질
- Seaborn/Matplotlib 활용
- 색상 구분 명확

---

## 📝 주요 통계 지표

### 성적 변동성
- `overall_volatility`: 전체 성적 표준편차
- `overall_cv`: 변동계수 (CV)
- `grade_change_mean`: 학기별 평균 변화량
- `{교과군}_volatility`: 교과군별 표준편차

### 세특 키워드 빈도
- `kw_freq_exploration`: 탐구 키워드 (per 1000 chars)
- `kw_freq_online`: 온라인 키워드 (per 1000 chars)

### 코호트 분류
- **Pre-COVID (0)**: 2018-2020 졸업 (입학년도 2015-2017)
- **COVID (1)**: 2021-2024 졸업 (입학년도 2018-2021)

---

## ⚙️ 기술 사양

### 환경 요구사항
- Python 3.7+
- 메모리: 1-2GB
- 디스크: 200MB

### 필수 패키지
```
pandas
numpy
scipy
statsmodels
matplotlib
seaborn
tqdm
```

### 파일명 형식
```
{학번}_3학년_{학과}_{이름}_{전형}_censored.txt

예시: 202110937_3학년_컴퓨터과학과_서형완_수시_censored.txt
```

---

## 🐛 문제 해결

### 자주 발생하는 오류

**1. 파싱 실패**
```bash
# 로그 확인
cat logs/parsing_errors.log

# 원인: 파일명 형식, 인코딩 문제, 텍스트 구조 특이
```

**2. 인코딩 오류**
```bash
# UTF-8로 변환
for file in data/raw/*.txt; do
    iconv -f EUC-KR -t UTF-8 "$file" > "${file}.utf8"
    mv "${file}.utf8" "$file"
done
```

**3. 메모리 부족**
- 배치 처리 활성화
- 한 번에 10개씩만 처리

**4. 통계 검정 오류**
```python
# 데이터 확인
import pandas as pd
df = pd.read_csv('data/processed/grades.csv')
print(df.describe())
print(df.isnull().sum())
```

---

## 📈 예상 결과 예시

### 코호트 비교 (예상치)

| 지표 | Pre-COVID | COVID | 차이 |
|------|-----------|-------|------|
| 평균 변동성 | 0.85 | 1.12 | +31.8% |
| 탐구 키워드 빈도 | 15.2 | 10.8 | -28.9% |
| 온라인 키워드 빈도 | 0.5 | 8.3 | +1560% |

### 가설 검증 결과 (예상)

**H1-1**: p < 0.05 → 유의함 (변동성 증가)
**H1-2**: 부분 매개효과 확인
**H1-3**: p < 0.01 → 유의함 (정성평가 강조)

---

## 🎓 활용 방안

### 1. 학술 연구
- 논문 작성: 그래프 + 통계 테이블 활용
- 학회 발표: PPT 자료로 변환

### 2. 정책 제안
- 교육부/교육청 정책 자료
- 대학 입시 개선 방안

### 3. 추가 분석
```python
# CSV 데이터로 자유로운 분석 가능
import pandas as pd
df = pd.read_csv('data/processed/grades.csv')
# ... 원하는 분석 수행
```

---

## 📞 문의 및 지원

실행 중 문제가 발생하면:
1. `logs/parsing_errors.log` 확인
2. 에러 메시지 캡처
3. 문제 상황 설명과 함께 문의

---

## ✅ 최종 체크리스트

**실행 전**:
- [ ] 69개 txt 파일 준비
- [ ] data/raw/ 디렉토리에 배치
- [ ] 파일명 형식 확인 ({학번}_3학년_{학과}_{이름}_{전형}_censored.txt)
- [ ] 패키지 설치 완료

**실행 중**:
- [ ] 각 단계별 진행 상황 확인
- [ ] 에러 발생 시 로그 확인

**실행 후**:
- [ ] data/processed/ 에 4개 CSV 생성 확인
- [ ] data/results/ 에 결과 CSV 생성 확인
- [ ] outputs/figures/ 에 그래프 생성 확인
- [ ] outputs/reports/ 에 리포트 생성 확인
- [ ] logs/parsing_errors.log 에 오류 없는지 확인

---

**프로젝트 완료!** 🎉

모든 코드와 문서가 준비되었습니다.
`bash run_all.sh` 명령어로 전체 분석을 실행하세요.