#!/bin/bash
# =============================================================================
# 생활기록부 분석 파이프라인 실행 스크립트
# =============================================================================
# 수정사항:
# - statsmodels 필수 설치 추가
# - thefuzz 필수 설치 (선택 → 필수)
# - 루트 디렉토리 가상환경 지원
# =============================================================================

set -e

echo "============================================================"
echo "🔬 생활기록부 분석 파이프라인"
echo "============================================================"

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# =============================================================================
# 가상환경 활성화
# =============================================================================
echo -e "\n${BLUE}[1/6] 가상환경 설정${NC}"

if [ -f "./bin/activate" ]; then
    echo "  🔄 가상환경 활성화 중... (루트 디렉토리)"
    source ./bin/activate
    echo -e "  ${GREEN}✅ 활성화 완료: $VIRTUAL_ENV${NC}"
elif [ -f "./venv/bin/activate" ]; then
    echo "  🔄 가상환경 활성화 중... (venv 폴더)"
    source ./venv/bin/activate
    echo -e "  ${GREEN}✅ 활성화 완료: $VIRTUAL_ENV${NC}"
elif [ -f "./Scripts/activate" ]; then
    echo "  🔄 가상환경 활성화 중... (Windows 루트)"
    source ./Scripts/activate
    echo -e "  ${GREEN}✅ 활성화 완료${NC}"
elif [ -f "./venv/Scripts/activate" ]; then
    echo "  🔄 가상환경 활성화 중... (Windows venv)"
    source ./venv/Scripts/activate
    echo -e "  ${GREEN}✅ 활성화 완료${NC}"
else
    echo -e "  ${YELLOW}⚠️ 가상환경 없음 - 시스템 Python 사용${NC}"
fi

# =============================================================================
# 필수 패키지 설치
# =============================================================================
echo -e "\n${BLUE}[2/6] 패키지 설치${NC}"

# 필수 패키지 목록 (thefuzz, statsmodels 포함!)
REQUIRED_PACKAGES="pandas numpy matplotlib seaborn scipy openpyxl thefuzz python-Levenshtein statsmodels"

echo "  📦 필수 패키지 설치 중..."
pip install $REQUIRED_PACKAGES -q 2>/dev/null || {
    echo "  ⚠️ pip install 실패 - 개별 설치 시도"
    for pkg in $REQUIRED_PACKAGES; do
        pip install $pkg -q 2>/dev/null || echo "    ⚠️ $pkg 설치 실패"
    done
}

# 설치 확인
echo "  📋 설치 확인:"
for pkg in pandas numpy matplotlib seaborn scipy openpyxl statsmodels; do
    if pip show $pkg > /dev/null 2>&1; then
        echo -e "    ${GREEN}✅ $pkg${NC}"
    else
        echo -e "    ${RED}❌ $pkg 미설치${NC}"
    fi
done

# thefuzz 특별 확인
if pip show thefuzz > /dev/null 2>&1; then
    echo -e "    ${GREEN}✅ thefuzz (퍼지 매칭)${NC}"
else
    echo -e "    ${RED}❌ thefuzz 미설치 - 텍스트 파싱 품질 저하${NC}"
    echo "    📦 재설치 시도..."
    pip install thefuzz python-Levenshtein -q 2>/dev/null || true
fi

# statsmodels 특별 확인
if pip show statsmodels > /dev/null 2>&1; then
    echo -e "    ${GREEN}✅ statsmodels (회귀분석)${NC}"
else
    echo -e "    ${RED}❌ statsmodels 미설치 - OLS 분석 불가${NC}"
    echo "    📦 재설치 시도..."
    pip install statsmodels -q 2>/dev/null || true
fi

# =============================================================================
# 한글 폰트 확인 (Linux)
# =============================================================================
echo -e "\n${BLUE}[3/6] 한글 폰트 확인${NC}"

if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    if fc-list 2>/dev/null | grep -i "nanum" > /dev/null 2>&1; then
        echo "  ✅ 나눔폰트 설치됨"
    else
        echo "  📦 나눔폰트 설치 시도..."
        sudo apt-get update -qq 2>/dev/null || true
        sudo apt-get install -y fonts-nanum -qq 2>/dev/null || echo "  ⚠️ 폰트 설치 실패"
        fc-cache -fv > /dev/null 2>&1 || true
    fi
elif [[ "$OSTYPE" == "darwin"* ]]; then
    echo "  ✅ Mac: AppleGothic"
else
    echo "  ✅ Windows: 맑은고딕"
fi

# =============================================================================
# 디렉토리 구조 생성
# =============================================================================
echo -e "\n${BLUE}[4/6] 디렉토리 생성${NC}"

mkdir -p data/raw
mkdir -p data/processed
mkdir -p data/results
mkdir -p outputs/figures
mkdir -p outputs/reports/individual
mkdir -p logs

echo "  ✅ 디렉토리 구조 준비 완료"

# =============================================================================
# 파이프라인 실행
# =============================================================================
echo -e "\n${BLUE}[5/6] 파이프라인 실행${NC}"

# Step 1
echo -e "\n  ${YELLOW}📄 Step 1: 데이터 파싱${NC}"
if [ -f "step1_parse_all_files.py" ]; then
    python step1_parse_all_files.py
    echo -e "  ${GREEN}✅ Step 1 완료${NC}"
else
    echo -e "  ${RED}❌ step1_parse_all_files.py 없음${NC}"
    exit 1
fi

# Step 2
echo -e "\n  ${YELLOW}📊 Step 2: 탐색적 분석${NC}"
if [ -f "step2_exploratory_analysis.py" ]; then
    python step2_exploratory_analysis.py
    echo -e "  ${GREEN}✅ Step 2 완료${NC}"
else
    echo "  ⚠️ step2 없음 - 건너뜀"
fi

# Step 3
echo -e "\n  ${YELLOW}🔬 Step 3: 가설 검증${NC}"
if [ -f "step3_hypothesis_testing.py" ]; then
    python step3_hypothesis_testing.py
    echo -e "  ${GREEN}✅ Step 3 완료${NC}"
else
    echo "  ⚠️ step3 없음 - 건너뜀"
fi

# Step 4
echo -e "\n  ${YELLOW}📈 Step 4: 시각화${NC}"
if [ -f "step4_visualization.py" ]; then
    python step4_visualization.py
    echo -e "  ${GREEN}✅ Step 4 완료${NC}"
else
    echo "  ⚠️ step4 없음 - 건너뜀"
fi

# Step 5
echo -e "\n  ${YELLOW}📝 Step 5: 보고서${NC}"
if [ -f "step5_generate_reports.py" ]; then
    python step5_generate_reports.py
    echo -e "  ${GREEN}✅ Step 5 완료${NC}"
else
    echo "  ⚠️ step5 없음 - 건너뜀"
fi

# =============================================================================
# 완료
# =============================================================================
echo -e "\n${BLUE}[6/6] 완료${NC}"
echo "============================================================"
echo -e "${GREEN}✅ 파이프라인 실행 완료!${NC}"
echo "============================================================"
echo ""
echo "📁 출력 파일:"
echo "   - data/processed/*.csv    (처리된 데이터)"
echo "   - data/results/*.csv      (통계 결과)"
echo "   - outputs/figures/*.png   (시각화)"
echo "   - outputs/reports/*.txt   (보고서)"
echo ""