"""
STEP 3: 가설 검증 (고급 통계 기법)
==================================
개선사항:
1. 용량-반응 관계(Dose-Response) 분석
2. 코로나 영향 강도 가중치 (0~3점)
3. step1과 완벽 호환

H1-1: 내신 성적의 변동성과 불안정성은 코로나 기간 코호트(2021~2024)에서 
      이전 코호트(2018~2020) 대비 통계적으로 유의미하게 증가했을 것이다.

작성일: 2025
"""

import pandas as pd
import numpy as np
from scipy import stats
from scipy.stats import ttest_ind, mannwhitneyu, levene, shapiro, spearmanr
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# statsmodels 임포트
try:
    import statsmodels.api as sm
    from statsmodels.formula.api import ols
    STATSMODELS_AVAILABLE = True
except ImportError:
    STATSMODELS_AVAILABLE = False
    print("⚠️  statsmodels 미설치 - 기본 분석만 수행")


def load_and_prepare_data(data_dir: str = "data/processed") -> dict:
    """데이터 로드 및 분석용 변수 생성"""
    data_path = Path(data_dir)
    
    # 학생 정보 로드 (여러 파일명 시도)
    df_students = None
    for filename in ['students_anonymized.csv', 'student_info.csv']:
        filepath = data_path / filename
        if filepath.exists():
            df_students = pd.read_csv(filepath)
            print(f"✓ 학생 정보 로드: {filename}")
            break
    
    if df_students is None:
        raise FileNotFoundError("학생 정보 파일을 찾을 수 없습니다.")
    
    df_grades = pd.read_csv(data_path / 'grades.csv')
    print(f"✓ 성적 로드: grades.csv")
    
    df_yearly = None
    yearly_path = data_path / 'yearly_covid.csv'
    if yearly_path.exists():
        df_yearly = pd.read_csv(yearly_path)
        print(f"✓ 연도별 코로나 로드: yearly_covid.csv")
    
    print(f"\n📂 데이터 로드 완료")
    print(f"   - 학생: {len(df_students)}명")
    print(f"   - 성적 레코드: {len(df_grades)}개")
    
    id_col = 'anonymous_id' if 'anonymous_id' in df_students.columns else 'student_id'
    
    if 'covid_intensity' not in df_students.columns:
        covid_cols = ['grade1_covid', 'grade2_covid', 'grade3_covid']
        available_cols = [c for c in covid_cols if c in df_students.columns]
        if available_cols:
            df_students['covid_intensity'] = df_students[available_cols].sum(axis=1)
        else:
            for col in ['any_covid', 'has_covid', 'has_covid_period', 'covid_period']:
                if col in df_students.columns:
                    df_students['covid_intensity'] = df_students[col].fillna(0).astype(int)
                    break
            else:
                df_students['covid_intensity'] = 0
    
    if 'has_covid' not in df_students.columns:
        df_students['has_covid'] = (df_students['covid_intensity'] > 0).astype(int)
    
    print(f"\n📊 코로나 영향 강도 분포:")
    for intensity in sorted(df_students['covid_intensity'].unique()):
        count = (df_students['covid_intensity'] == intensity).sum()
        pct = count / len(df_students) * 100
        print(f"   - 강도 {int(intensity)}: {count}명 ({pct:.1f}%)")
    
    volatility = df_grades.groupby('student_id').agg({
        'grade_numeric': ['std', 'mean', 'count', 'min', 'max']
    }).reset_index()
    volatility.columns = [id_col, 'volatility', 'mean_grade', 'grade_count', 'min_grade', 'max_grade']
    volatility['grade_range'] = volatility['max_grade'] - volatility['min_grade']
    volatility['cv'] = volatility['volatility'] / volatility['mean_grade']
    
    df_analysis = df_students.merge(volatility, on=id_col, how='inner')
    df_analysis = df_analysis.dropna(subset=['volatility'])
    
    print(f"\n📊 분석 대상: {len(df_analysis)}명")
    
    return {'students': df_students, 'grades': df_grades, 'yearly': df_yearly, 'analysis': df_analysis}


def descriptive_statistics(df: pd.DataFrame) -> pd.DataFrame:
    print("\n" + "="*70)
    print("📊 기술 통계: 코로나 영향 강도별 성적 변동성")
    print("="*70)
    
    if 'covid_intensity' not in df.columns:
        return pd.DataFrame()
    
    stats_df = df.groupby('covid_intensity').agg({
        'volatility': ['count', 'mean', 'std', 'median', 'min', 'max']
    }).round(4)
    print(stats_df)
    return stats_df


def assumption_tests(df: pd.DataFrame) -> dict:
    print("\n" + "="*70)
    print("🔬 가정 검정 (Assumption Tests)")
    print("="*70)
    
    results = {}
    if 'covid_intensity' not in df.columns:
        return results
    
    print("\n[1] Shapiro-Wilk 정규성 검정")
    for intensity in sorted(df['covid_intensity'].unique()):
        group_data = df[df['covid_intensity'] == intensity]['volatility'].dropna()
        if len(group_data) >= 3:
            stat, p = shapiro(group_data[:50])
            normality = "정규" if p > 0.05 else "비정규"
            print(f"   강도 {int(intensity)}: W={stat:.4f}, p={p:.4f} → {normality}")
    
    print("\n[2] Levene 등분산성 검정")
    groups = [df[df['covid_intensity'] == i]['volatility'].dropna() 
              for i in sorted(df['covid_intensity'].unique()) if len(df[df['covid_intensity'] == i]) >= 3]
    if len(groups) >= 2:
        stat, p = levene(*groups)
        print(f"   Levene's test: W={stat:.4f}, p={p:.4f}")
    
    return results


def dose_response_analysis(df: pd.DataFrame) -> dict:
    print("\n" + "="*70)
    print("📈 용량-반응 관계 분석")
    print("="*70)
    
    results = {}
    if 'covid_intensity' not in df.columns:
        return results
    
    print("\n[1] OLS 회귀분석: 변동성 ~ 코로나_강도")
    print("-"*50)
    
    slope, intercept, r_value, p_value, std_err = stats.linregress(
        df['covid_intensity'], df['volatility']
    )
    print(f"   β₀ (절편): {intercept:.4f}")
    print(f"   β₁ (기울기): {slope:.4f}")
    print(f"   R² = {r_value**2:.4f}")
    print(f"   p-value = {p_value:.6f}")
    print(f"   해석: 코로나 영향 학년이 1년 증가할 때마다 변동성이 {slope:.4f} {'증가' if slope > 0 else '감소'}")
    
    significance = "유의함 ✅" if p_value < 0.05 else "유의하지 않음 ❌"
    print(f"   → 모델 유의성: {significance}")
    
    results['ols_basic'] = {'intercept': intercept, 'slope': slope, 'r_squared': r_value**2, 'p_value': p_value}
    
    print("\n[2] Spearman 순위 상관분석")
    print("-"*50)
    rho, p = spearmanr(df['covid_intensity'], df['volatility'])
    print(f"   Spearman's ρ = {rho:.4f}, p-value = {p:.6f}")
    results['spearman'] = {'rho': rho, 'p_value': p}
    
    return results


def effect_size_analysis(df: pd.DataFrame) -> dict:
    print("\n" + "="*70)
    print("📏 효과 크기 분석")
    print("="*70)
    
    results = {}
    if 'covid_intensity' not in df.columns:
        return results
    
    group_0 = df[df['covid_intensity'] == 0]['volatility'].dropna()
    group_pos = df[df['covid_intensity'] > 0]['volatility'].dropna()
    
    if len(group_0) >= 2 and len(group_pos) >= 2:
        n1, n2 = len(group_0), len(group_pos)
        s1, s2 = group_0.std(), group_pos.std()
        pooled_std = np.sqrt(((n1-1)*s1**2 + (n2-1)*s2**2) / (n1+n2-2))
        
        if pooled_std > 0:
            cohens_d = (group_pos.mean() - group_0.mean()) / pooled_std
            print(f"\n[1] Cohen's d = {cohens_d:.4f}")
            results['cohens_d'] = cohens_d
    
    groups = [df[df['covid_intensity'] == i]['volatility'].dropna() 
              for i in sorted(df['covid_intensity'].unique()) if len(df[df['covid_intensity'] == i]) >= 2]
    
    if len(groups) >= 2:
        f_stat, p_value = stats.f_oneway(*groups)
        grand_mean = df['volatility'].mean()
        ss_between = sum(len(g) * (g.mean() - grand_mean)**2 for g in groups)
        ss_total = sum((df['volatility'] - grand_mean)**2)
        eta_squared = ss_between / ss_total if ss_total > 0 else 0
        
        print(f"\n[2] ANOVA: F={f_stat:.4f}, p={p_value:.6f}, η²={eta_squared:.4f}")
        results['eta_squared'] = eta_squared
        results['anova_p'] = p_value
    
    return results


def bootstrap_confidence_interval(df: pd.DataFrame, n_bootstrap: int = 500) -> dict:
    print("\n" + "="*70)
    print("🔄 부트스트랩 신뢰구간")
    print("="*70)
    
    if 'covid_intensity' not in df.columns:
        return {}
    
    slopes = []
    for _ in range(n_bootstrap):
        sample = df.sample(n=len(df), replace=True)
        try:
            slope, _, _, _, _ = stats.linregress(sample['covid_intensity'], sample['volatility'])
            slopes.append(slope)
        except:
            continue
    
    slopes = np.array(slopes)
    ci_lower, ci_upper = np.percentile(slopes, [2.5, 97.5])
    
    print(f"   평균: {np.mean(slopes):.4f}")
    print(f"   95% CI: [{ci_lower:.4f}, {ci_upper:.4f}]")
    
    if ci_lower > 0:
        print("   → 양의 효과 유의함 ✅")
    elif ci_upper < 0:
        print("   → 음의 효과 유의함")
    else:
        print("   → 0이 CI에 포함됨 ❌")
    
    return {'mean_slope': np.mean(slopes), 'ci_lower': ci_lower, 'ci_upper': ci_upper}


def summary_report(all_results: dict) -> None:
    print("\n" + "="*70)
    print("📋 H1-1 가설 검증 종합 결과")
    print("="*70)
    
    significant = 0
    total = 0
    
    if 'dose_response' in all_results:
        if all_results['dose_response'].get('ols_basic', {}).get('p_value', 1) < 0.05:
            significant += 1
        total += 1
        if all_results['dose_response'].get('spearman', {}).get('p_value', 1) < 0.05:
            significant += 1
        total += 1
    
    if 'effect_size' in all_results and all_results['effect_size'].get('anova_p', 1) < 0.05:
        significant += 1
        total += 1
    
    print(f"\n   유의한 검정: {significant}/{total}")
    
    if total > 0 and significant >= total * 0.5:
        print("\n   ✅ H1-1 가설 지지: 코로나 강도 증가에 따른 변동성 증가 경향 확인")
    else:
        print("\n   ❌ H1-1 가설 불충분: 추가 데이터 필요")


def save_results(all_results: dict, df_analysis: pd.DataFrame, output_dir: str = "data/results"):
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    df_analysis.to_csv(output_path / 'h1_1_analysis_data.csv', index=False)
    
    hypothesis_results = []
    if 'dose_response' in all_results:
        dr = all_results['dose_response']
        hypothesis_results.append({
            'hypothesis': 'H1-1',
            'test': 'OLS Regression',
            'statistic': dr.get('ols_basic', {}).get('slope'),
            'p_value': dr.get('ols_basic', {}).get('p_value'),
            'conclusion': 'Supported' if dr.get('ols_basic', {}).get('p_value', 1) < 0.05 else 'Not Supported'
        })
    
    pd.DataFrame(hypothesis_results).to_csv(output_path / 'hypothesis_tests.csv', index=False)
    
    if 'covid_intensity' in df_analysis.columns:
        summary = df_analysis.groupby('covid_intensity').agg({
            'volatility': ['mean', 'std', 'count']
        }).reset_index()
        summary.columns = ['cohort', 'avg_volatility', 'std_volatility', 'n']
        summary.to_csv(output_path / 'summary_statistics.csv', index=False)
    
    print(f"\n📁 결과 저장: {output_path}")


def main():
    print("="*70)
    print("🔬 H1-1 가설 검증: 용량-반응 분석")
    print("="*70)
    
    try:
        data = load_and_prepare_data()
        df = data['analysis']
        
        if len(df) < 5:
            print("⚠️  분석 대상 부족")
            return
        
        all_results = {}
        descriptive_statistics(df)
        all_results['assumptions'] = assumption_tests(df)
        all_results['dose_response'] = dose_response_analysis(df)
        all_results['effect_size'] = effect_size_analysis(df)
        all_results['bootstrap'] = bootstrap_confidence_interval(df)
        summary_report(all_results)
        save_results(all_results, df)
        
        return all_results
        
    except FileNotFoundError as e:
        print(f"\n❌ {e}\n먼저 step1을 실행하세요!")
    except Exception as e:
        print(f"\n❌ 오류: {e}")


if __name__ == "__main__":
    results = main()