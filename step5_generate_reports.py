"""
STEP 5: 보고서 생성
==================
step1~step4와 완벽 호환

작성일: 2025
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime


def load_all_data():
    """모든 데이터 로드"""
    data_dir = Path('data/processed')
    results_dir = Path('data/results')
    
    # 학생 정보 (여러 파일명 호환)
    df_students = None
    for filename in ['student_info.csv', 'students_anonymized.csv']:
        filepath = data_dir / filename
        if filepath.exists():
            df_students = pd.read_csv(filepath)
            break
    
    if df_students is None:
        df_students = pd.DataFrame()
    
    # 기타 파일
    df_grades = pd.read_csv(data_dir / 'grades.csv') if (data_dir / 'grades.csv').exists() else pd.DataFrame()
    df_seteuk = pd.read_csv(data_dir / 'seteuk.csv') if (data_dir / 'seteuk.csv').exists() else pd.DataFrame()
    df_volatility = pd.read_csv(data_dir / 'volatility.csv') if (data_dir / 'volatility.csv').exists() else pd.DataFrame()
    
    # 결과 파일
    df_hypothesis = pd.read_csv(results_dir / 'hypothesis_tests.csv') if (results_dir / 'hypothesis_tests.csv').exists() else None
    df_summary = pd.read_csv(results_dir / 'summary_statistics.csv') if (results_dir / 'summary_statistics.csv').exists() else None
    
    return df_students, df_grades, df_seteuk, df_volatility, df_hypothesis, df_summary


def get_covid_col(df):
    """코로나 컬럼 찾기"""
    for col in ['covid_period', 'any_covid', 'has_covid', 'has_covid_period']:
        if col in df.columns:
            return col
    return None


def generate_individual_report(student_id, df_students, df_grades, df_seteuk, df_volatility):
    """개별 학생 리포트"""
    id_col = 'anonymous_id' if 'anonymous_id' in df_students.columns else 'student_id'
    
    student = df_students[df_students[id_col] == student_id]
    if student.empty:
        return None
    student = student.iloc[0]
    
    grades = df_grades[df_grades['student_id'] == student_id]
    seteuk = df_seteuk[df_seteuk['student_id'] == student_id] if not df_seteuk.empty else pd.DataFrame()
    volatility = df_volatility[df_volatility['student_id'] == student_id] if not df_volatility.empty else pd.DataFrame()
    
    report = []
    report.append("="*80)
    report.append("개별 학생 분석 리포트")
    report.append("="*80)
    report.append("")
    
    report.append("[학생 정보]")
    report.append(f"ID: {student_id[:8]}... (비식별화)")
    
    if 'grade' in student.index:
        report.append(f"학년: {student['grade']}")
    if 'major' in student.index:
        report.append(f"전공: {student['major']}")
    if 'admission_type' in student.index:
        report.append(f"전형: {student['admission_type']}")
    
    covid_col = get_covid_col(df_students)
    if covid_col and covid_col in student.index:
        cohort = 'COVID' if student[covid_col] == 1 else 'Pre-COVID'
        report.append(f"코호트: {cohort}")
    
    if 'covid_intensity' in student.index:
        report.append(f"코로나 영향 강도: {int(student['covid_intensity'])}학년")
    
    report.append("")
    report.append("[성적 요약]")
    report.append(f"총 과목 수: {len(grades)}")
    
    if not grades.empty and 'grade_numeric' in grades.columns:
        report.append(f"평균 등급: {grades['grade_numeric'].mean():.2f}")
        
        if 'achievement' in grades.columns:
            for grade in ['A', 'B', 'C', 'D', 'E']:
                count = (grades['achievement'] == grade).sum()
                if count > 0:
                    report.append(f"  {grade} 등급: {count}개")
    
    report.append("")
    report.append("[성적 변동성]")
    if not volatility.empty:
        vol_data = volatility.iloc[0]
        if 'overall_volatility' in vol_data.index:
            report.append(f"전체 변동성: {vol_data['overall_volatility']:.3f}")
        if 'overall_mean' in vol_data.index:
            report.append(f"전체 평균: {vol_data['overall_mean']:.3f}")
    
    report.append("")
    report.append("[세특 요약]")
    report.append(f"총 세특 개수: {len(seteuk)}")
    if not seteuk.empty and 'content_length' in seteuk.columns:
        report.append(f"평균 길이: {seteuk['content_length'].mean():.0f}자")
    
    report.append("")
    report.append("="*80)
    report.append(f"생성일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("="*80)
    
    return '\n'.join(report)


def generate_comprehensive_report(df_students, df_grades, df_seteuk, df_volatility, df_hypothesis, df_summary):
    """전체 종합 리포트"""
    
    report = []
    report.append("="*80)
    report.append("COVID-19 대학입시 영향 분석 종합 리포트")
    report.append("="*80)
    report.append("")
    
    report.append("[1. 연구 개요]")
    report.append("본 연구는 COVID-19 팬데믹이 한국 고등학생의 내신 성적, 학생부, 그리고")
    report.append("대학 입시 전형에 미친 영향을 정량적으로 분석합니다.")
    report.append("")
    report.append("분석 대상:")
    report.append(f"  - 총 학생 수: {len(df_students)}명 (비식별화)")
    
    covid_col = get_covid_col(df_students)
    if covid_col and covid_col in df_students.columns:
        pre_covid = (df_students[covid_col] == 0).sum()
        has_covid = (df_students[covid_col] == 1).sum()
        report.append(f"  - Pre-COVID 코호트: {pre_covid}명")
        report.append(f"  - COVID 코호트: {has_covid}명")
    
    if 'covid_intensity' in df_students.columns:
        report.append("")
        report.append("코로나 영향 강도 분포:")
        for intensity in sorted(df_students['covid_intensity'].unique()):
            count = (df_students['covid_intensity'] == intensity).sum()
            report.append(f"  - {int(intensity)}학년 영향: {count}명")
    
    report.append(f"  - 총 성적 레코드: {len(df_grades)}건")
    report.append(f"  - 총 세특 레코드: {len(df_seteuk)}건")
    report.append("")
    
    report.append("[2. 가설 검증 결과]")
    report.append("")
    
    if df_hypothesis is not None and not df_hypothesis.empty:
        for _, row in df_hypothesis.iterrows():
            report.append(f"{row.get('hypothesis', 'N/A')} - {row.get('test', 'N/A')}:")
            if 'conclusion' in row:
                report.append(f"  결과: {row['conclusion']}")
            if 'p_value' in row and pd.notna(row['p_value']):
                report.append(f"  p-value: {row['p_value']:.4f}")
            report.append("")
    else:
        report.append("  가설 검증 결과를 찾을 수 없습니다.")
        report.append("")
    
    report.append("[3. 주요 발견사항]")
    report.append("")
    
    if df_summary is not None and not df_summary.empty:
        report.append("코로나 강도별 변동성:")
        for _, row in df_summary.iterrows():
            cohort = row.get('cohort', 'N/A')
            avg_vol = row.get('avg_volatility', 'N/A')
            n = row.get('n', 'N/A')
            if pd.notna(avg_vol):
                report.append(f"  - 강도 {int(cohort)}: 평균 변동성 {avg_vol:.3f} (n={int(n)})")
        report.append("")
    
    report.append("[4. 결론 및 시사점]")
    report.append("")
    report.append("본 연구는 COVID-19 팬데믹이 한국 교육 시스템에 미친 영향을 분석했습니다.")
    report.append("용량-반응 관계(Dose-Response) 분석을 통해 코로나 영향 학년 수에 따른")
    report.append("성적 변동성의 변화를 검증했습니다.")
    report.append("")
    
    report.append("[5. 연구의 한계]")
    report.append("")
    report.append(f"  - 제한된 표본 크기 (n={len(df_students)})")
    report.append("  - 특정 대학의 지원자 데이터에 국한")
    report.append("  - 실제 합격 결과 데이터 미포함")
    report.append("")
    
    report.append("="*80)
    report.append(f"생성일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("="*80)
    
    return '\n'.join(report)


def main():
    """메인 실행 함수"""
    
    print("="*80)
    print("STEP 5: 보고서 생성")
    print("="*80)
    
    print("\n데이터 로딩 중...")
    df_students, df_grades, df_seteuk, df_volatility, df_hypothesis, df_summary = load_all_data()
    
    if df_students.empty:
        print("❌ 학생 데이터가 없습니다. step1을 먼저 실행하세요!")
        return
    
    print(f"✓ 학생: {len(df_students)}명")
    print(f"✓ 성적: {len(df_grades)}건")
    
    # 출력 디렉토리
    individual_dir = Path('outputs/reports/individual')
    individual_dir.mkdir(parents=True, exist_ok=True)
    comprehensive_dir = Path('outputs/reports')
    
    # 개별 리포트 생성
    id_col = 'anonymous_id' if 'anonymous_id' in df_students.columns else 'student_id'
    
    print(f"\n개별 리포트 생성 중 ({len(df_students)}개)...")
    for _, student in df_students.iterrows():
        student_id = student[id_col]
        
        report_content = generate_individual_report(
            student_id, df_students, df_grades, df_seteuk, df_volatility
        )
        
        if report_content:
            filename = f"report_{student_id[:8]}.txt"
            with open(individual_dir / filename, 'w', encoding='utf-8') as f:
                f.write(report_content)
    
    print(f"✓ {len(df_students)}개 개별 리포트 생성")
    
    # 종합 리포트 생성
    print("\n종합 리포트 생성 중...")
    comprehensive_report = generate_comprehensive_report(
        df_students, df_grades, df_seteuk, df_volatility, df_hypothesis, df_summary
    )
    
    with open(comprehensive_dir / 'comprehensive_report.txt', 'w', encoding='utf-8') as f:
        f.write(comprehensive_report)
    
    print("✓ 종합 리포트 생성")
    
    print("\n" + "="*80)
    print("✅ 보고서 생성 완료!")
    print("="*80)
    print(f"\n개별 리포트: {individual_dir}")
    print(f"종합 리포트: {comprehensive_dir / 'comprehensive_report.txt'}")
    
    print("\n" + "="*80)
    print("🎉 전체 분석 파이프라인 완료!")
    print("="*80)
    print("\n생성된 결과물:")
    print("  1. data/processed/ - 처리된 데이터 (CSV)")
    print("  2. data/results/ - 통계 분석 결과 (CSV)")
    print("  3. outputs/figures/ - 시각화 결과 (PNG)")
    print("  4. outputs/reports/ - 분석 리포트 (TXT)")


if __name__ == "__main__":
    main()