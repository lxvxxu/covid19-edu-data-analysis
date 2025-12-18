"""
STEP 2: 탐색적 데이터 분석 (EDA)
================================
- 빈 파일 처리 추가
- 여러 파일명 호환
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import platform
from matplotlib import font_manager, rc
import warnings
warnings.filterwarnings('ignore')


def set_korean_font():
    """OS별 한글 폰트 설정"""
    system = platform.system()
    if system == 'Windows':
        try:
            rc('font', family='Malgun Gothic')
        except:
            pass
    elif system == 'Darwin':
        rc('font', family='AppleGothic')
    else:
        try:
            font_list = [f.name for f in font_manager.fontManager.ttflist]
            if 'NanumGothic' in font_list:
                rc('font', family='NanumGothic')
        except:
            pass
    plt.rcParams['axes.unicode_minus'] = False


set_korean_font()


def load_data():
    """데이터 로드 (빈 파일 및 여러 파일명 호환)"""
    data_dir = Path('data/processed')
    
    # 안전한 CSV 로드 함수
    def safe_load(filenames):
        if isinstance(filenames, str):
            filenames = [filenames]
        for filename in filenames:
            filepath = data_dir / filename
            if filepath.exists():
                try:
                    df = pd.read_csv(filepath)
                    if not df.empty:
                        print(f"  ✅ {filename} ({len(df)} rows)")
                        return df
                except Exception as e:
                    print(f"  ⚠️ {filename}: {e}")
        print(f"  ⚠️ {filenames[0]} 없음/빈 파일")
        return pd.DataFrame()
    
    df_students = safe_load(['student_info.csv', 'students_anonymized.csv'])
    df_grades = safe_load('grades.csv')
    df_seteuk = safe_load('seteuk.csv')
    df_volatility = safe_load('volatility.csv')
    
    return df_students, df_grades, df_seteuk, df_volatility


def descriptive_statistics(df_students, df_grades, df_seteuk, df_volatility):
    """기술통계"""
    
    print("\n" + "="*80)
    print("1. 기술통계량")
    print("="*80)
    
    # 학생 정보
    print("\n[학생 정보]")
    print(f"총 학생 수: {len(df_students)}")
    
    if df_students.empty:
        print("  ⚠️ 학생 데이터 없음")
        return
    
    # 코로나 관련 컬럼 찾기
    covid_col = None
    for col in ['any_covid', 'has_covid', 'has_covid_period', 'covid_period']:
        if col in df_students.columns:
            covid_col = col
            break
    
    if covid_col:
        print(f"\n코로나 경험:")
        print(f"  있음: {(df_students[covid_col]==1).sum()}명")
        print(f"  없음: {(df_students[covid_col]==0).sum()}명")
    
    # 코로나 강도
    if 'covid_intensity' in df_students.columns:
        print(f"\n코로나 영향 강도 분포 (영향받은 학년 수):")
        for intensity in sorted(df_students['covid_intensity'].unique()):
            count = (df_students['covid_intensity'] == intensity).sum()
            if intensity == 0:
                label = "미경험 (0개 학년)"
            else:
                label = f"{int(intensity)}개 학년 영향"
            print(f"  {label}: {count}명")
    
    # 학년별 코로나
    print(f"\n학년별 코로나 경험 (중복 가능 - 한 학생이 여러 학년 해당):")
    for grade in [1, 2, 3]:
        col = f'grade{grade}_covid'
        if col in df_students.columns:
            count = (df_students[col] == 1).sum()
            print(f"  {grade}학년 때 코로나: {count}명")
    
    # 졸업년도
    year_col = None
    for col in ['hs_graduation_year', 'graduation_year', 'grade_year_3']:
        if col in df_students.columns:
            year_col = col
            break
    
    if year_col:
        print(f"\n고교 졸업년도 분포:")
        year_dist = df_students[year_col].dropna().astype(int).value_counts().sort_index()
        for year, count in year_dist.items():
            print(f"  {year}년: {count}명")
    
    # 전공
    if 'major' in df_students.columns:
        print(f"\n전공 분포:")
        major_dist = df_students['major'].value_counts()
        for major, count in major_dist.head(10).items():
            print(f"  {major}: {count}명")
    
    # 성적 정보
    print(f"\n[성적 정보]")
    print(f"총 성적 레코드: {len(df_grades)}건")
    
    if not df_grades.empty:
        if 'grade_type' in df_grades.columns:
            print(f"\n평가 방식:")
            for gtype in df_grades['grade_type'].unique():
                count = (df_grades['grade_type'] == gtype).sum()
                type_name = '절대평가' if gtype == 'achievement' else '상대평가'
                print(f"  {type_name}: {count}건")
        
        if 'subject_group' in df_grades.columns:
            print(f"\n교과군별 과목 수:")
            group_dist = df_grades['subject_group'].value_counts()
            for group, count in group_dist.head(10).items():
                print(f"  {group}: {count}건")
        
        if 'grade_year' in df_grades.columns:
            print(f"\n학년별 성적 건수:")
            for grade in [1, 2, 3]:
                count = (df_grades['grade_year'] == grade).sum()
                if count > 0:
                    print(f"  {grade}학년: {count}건")
    
    # 세특 정보
    print(f"\n[세특 정보]")
    print(f"총 세특 레코드: {len(df_seteuk)}건")
    
    if not df_seteuk.empty and 'content_length' in df_seteuk.columns:
        print(f"평균 세특 길이: {df_seteuk['content_length'].mean():.1f}자")
    
    # 변동성 정보
    print(f"\n[변동성 정보]")
    
    if not df_volatility.empty and 'overall_volatility' in df_volatility.columns:
        valid = df_volatility['overall_volatility'].dropna()
        if len(valid) > 0:
            print(f"전체 평균 변동성: {valid.mean():.3f} ± {valid.std():.3f}")


def covid_comparison(df_students, df_grades, df_volatility):
    """코로나 그룹 비교"""
    
    print("\n" + "="*80)
    print("2. 코로나 그룹 비교")
    print("="*80)
    
    if df_students.empty:
        print("⚠️ 학생 데이터 없음")
        return
    
    # 코로나 컬럼 찾기
    covid_col = None
    for col in ['any_covid', 'has_covid', 'has_covid_period', 'covid_period']:
        if col in df_students.columns:
            covid_col = col
            break
    
    if not covid_col:
        print("⚠️ 코로나 정보 없음")
        return
    
    no_covid = df_students[df_students[covid_col] == 0]
    has_covid = df_students[df_students[covid_col] == 1]
    
    print(f"\n[전체 비교]")
    print(f"코로나 없음: {len(no_covid)}명")
    print(f"코로나 있음: {len(has_covid)}명")
    
    # 변동성 비교
    if not df_volatility.empty and 'overall_volatility' in df_volatility.columns:
        id_col = 'anonymous_id' if 'anonymous_id' in df_students.columns else 'student_id'
        
        vol_no = df_volatility[df_volatility['student_id'].isin(no_covid[id_col])]['overall_volatility'].dropna()
        vol_yes = df_volatility[df_volatility['student_id'].isin(has_covid[id_col])]['overall_volatility'].dropna()
        
        if len(vol_no) > 0 and len(vol_yes) > 0:
            print(f"\n전체 변동성:")
            print(f"  코로나 없음: {vol_no.mean():.3f} ± {vol_no.std():.3f}")
            print(f"  코로나 있음: {vol_yes.mean():.3f} ± {vol_yes.std():.3f}")
            print(f"  차이: {vol_yes.mean() - vol_no.mean():+.3f}")


def grade_distribution(df_grades):
    """등급 분포"""
    
    print("\n" + "="*80)
    print("3. 등급 분포")
    print("="*80)
    
    if df_grades.empty:
        print("⚠️ 성적 데이터 없음")
        return
    
    if 'achievement' not in df_grades.columns:
        print("⚠️ 등급 정보 없음")
        return
    
    print(f"\n[전체 등급 분포]")
    dist = df_grades['achievement'].value_counts().sort_index()
    for grade, count in dist.items():
        pct = count / len(df_grades) * 100
        print(f"  {grade}: {count}건 ({pct:.1f}%)")


def create_visualizations(df_students, df_grades, df_volatility):
    """시각화"""
    
    print("\n" + "="*80)
    print("4. 시각화 생성")
    print("="*80)
    
    output_dir = Path('outputs/figures')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if df_students.empty:
        print("⚠️ 데이터 부족 - 시각화 건너뜀")
        return
    
    # 코로나 컬럼 찾기
    covid_col = None
    for col in ['any_covid', 'has_covid', 'has_covid_period', 'covid_period']:
        if col in df_students.columns:
            covid_col = col
            break
    
    # 1. 코로나 경험 분포
    if covid_col:
        try:
            plt.figure(figsize=(8, 6))
            covid_counts = df_students[covid_col].value_counts().sort_index()
            labels = ['No COVID', 'Has COVID']
            colors = ['#4CAF50', '#F44336']
            plt.pie(covid_counts.values, labels=labels, colors=colors, autopct='%1.1f%%')
            plt.title('COVID-19 Exposure Distribution', fontsize=14, fontweight='bold')
            plt.tight_layout()
            plt.savefig(output_dir / 'eda_covid_exposure.png', dpi=150)
            plt.close()
            print("  ✅ eda_covid_exposure.png")
        except Exception as e:
            print(f"  ⚠️ 코로나 분포 시각화 실패: {e}")
    
    # 2. 변동성 분포
    if not df_volatility.empty and 'overall_volatility' in df_volatility.columns:
        try:
            valid_vol = df_volatility['overall_volatility'].dropna()
            if len(valid_vol) > 0:
                plt.figure(figsize=(10, 6))
                plt.hist(valid_vol, bins=20, color='steelblue', alpha=0.7, edgecolor='black')
                plt.axvline(valid_vol.mean(), color='red', linestyle='--', label=f'Mean: {valid_vol.mean():.3f}')
                plt.xlabel('Volatility', fontsize=12)
                plt.ylabel('Frequency', fontsize=12)
                plt.title('Grade Volatility Distribution', fontsize=14, fontweight='bold')
                plt.legend()
                plt.tight_layout()
                plt.savefig(output_dir / 'eda_volatility_dist.png', dpi=150)
                plt.close()
                print("  ✅ eda_volatility_dist.png")
        except Exception as e:
            print(f"  ⚠️ 변동성 분포 시각화 실패: {e}")
    
    print(f"\n✅ 시각화 저장: {output_dir}")


def main():
    """메인 함수"""
    
    print("\n" + "="*80)
    print("STEP 2: 탐색적 데이터 분석 (EDA)")
    print("="*80)
    
    print("\n데이터 로딩 중...")
    try:
        df_students, df_grades, df_seteuk, df_volatility = load_data()
    except Exception as e:
        print(f"❌ 데이터 로드 실패: {e}")
        return
    
    if df_students.empty:
        print("❌ 학생 데이터가 없습니다. step1을 먼저 실행하세요!")
        return
    
    print("✓ 데이터 로드 완료")
    
    # 분석
    descriptive_statistics(df_students, df_grades, df_seteuk, df_volatility)
    covid_comparison(df_students, df_grades, df_volatility)
    grade_distribution(df_grades)
    create_visualizations(df_students, df_grades, df_volatility)
    
    print("\n" + "="*80)
    print("✅ EDA 완료!")
    print("="*80)


if __name__ == "__main__":
    main()