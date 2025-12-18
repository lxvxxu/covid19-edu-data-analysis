#!/bin/bash
# =============================================================================
# 생활기록부 분석 파이프라인 실행 스크립트
# =============================================================================
# 개선사항:
# 1. 가상환경 자동 생성 및 활성화 (경로 오류 수정!)
# 2. 필요 패키지 자동 설치
# 3. 한글 폰트 자동 설치 (Linux)
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
# 가상환경 설정 (경로 오류 수정!)
# =============================================================================
VENV_DIR="venv"

echo -e "\n${BLUE}[1/6] 가상환경 설정${NC}"

if [ ! -d "$VENV_DIR" ]; then
    echo "  📦 가상환경 생성 중..."
    python3 -m venv $VENV_DIR
    echo -e "  ${GREEN}✅ 가상환경 생성: $VENV_DIR${NC}"
else
    echo "  ✅ 기존 가상환경: $VENV_DIR"
fi

# ⚠️ 수정된 부분: ./bin/activate → ./$VENV_DIR/bin/activate
echo "  🔄 가상환경 활성화..."
source ./$VENV_DIR/bin/activate

if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "  ${RED}❌ 가상환경 활성화 실패${NC}"
    exit 1
fi
echo -e "  ${GREEN}✅ 활성화: $VIRTUAL_ENV${NC}"

# =============================================================================
# 패키지 설치
# =============================================================================
echo -e "\n${BLUE}[2/6] 패키지 설치${NC}"

pip install --upgrade pip -q

PACKAGES="pandas numpy matplotlib seaborn scipy openpyxl"

# thefuzz 옵션 (Levenshtein Distance)
if pip show thefuzz > /dev/null 2>&1; then
    echo "  ✅ thefuzz 이미 설치됨"
else
    echo "  📦 thefuzz 설치 중..."
    pip install thefuzz python-Levenshtein -q 2>/dev/null || echo "  ⚠️ thefuzz 설치 실패 (선택사항)"
fi

for pkg in $PACKAGES; do
    if pip show $pkg > /dev/null 2>&1; then
        echo "  ✅ $pkg"
    else
        echo "  📦 $pkg 설치 중..."
        pip install $pkg -q
    fi
done

# statsmodels (선택)
if ! pip show statsmodels > /dev/null 2>&1; then
    echo "  📦 statsmodels 설치 중..."
    pip install statsmodels -q 2>/dev/null || echo "  ⚠️ statsmodels 설치 실패 (선택사항)"
fi

# =============================================================================
# 한글 폰트 설치 (Linux)
# =============================================================================
echo -e "\n${BLUE}[3/6] 한글 폰트 확인${NC}"

if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    if fc-list 2>/dev/null | grep -i "nanum" > /dev/null 2>&1; then
        echo "  ✅ 나눔폰트 설치됨"
    else
        echo "  📦 나눔폰트 설치 시도..."
        if command -v apt-get &> /dev/null; then
            sudo apt-get update -qq 2>/dev/null
            sudo apt-get install -y fonts-nanum -qq 2>/dev/null || echo "  ⚠️ 폰트 설치 실패"
            fc-cache -fv > /dev/null 2>&1 || true
        fi
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

echo "  ✅ 디렉토리 구조 생성 완료"

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
echo "🔒 개인정보 보호:"
echo "   - 학생 이름/학번: SHA-256 해싱으로 비식별화"
echo ""
echo -e "${YELLOW}💡 가상환경 비활성화: deactivate${NC}"
echo ""