"""
STEP 4: 시각화 생성
===================
개선사항:
1. OS별 한글 폰트 자동 설정
2. step1과 완벽 호환
3. 용량-반응 시각화 추가

작성일: 2025
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib import font_manager, rc
import platform
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')


def set_korean_font():
    """OS별 한글 폰트 자동 설정"""
    system = platform.system()
    
    if system == 'Windows':
        try:
            font_path = "c:/Windows/Fonts/malgun.ttf"
            font_name = font_manager.FontProperties(fname=font_path).get_name()
            rc('font', family=font_name)
            print(f"✅ 폰트: {font_name} (Windows)")
        except:
            rc('font', family='Malgun Gothic')
    elif system == 'Darwin':
        rc('font', family='AppleGothic')
        print("✅ 폰트: AppleGothic (Mac)")
    else:
        try:
            font_list = [f.name for f in font_manager.fontManager.ttflist]
            if 'NanumGothic' in font_list:
                rc('font', family='NanumGothic')
                print("✅ 폰트: NanumGothic (Linux)")
            else:
                rc('font', family='DejaVu Sans')
        except:
            rc('font', family='DejaVu Sans')
    
    plt.rcParams['axes.unicode_minus'] = False


set_korean_font()


def load_data(data_dir: str = "data/processed") -> dict:
    """데이터 로드"""
    data_path = Path(data_dir)
    data = {}
    
    # 학생 정보
    for filename in ['students_anonymized.csv', 'student_info.csv']:
        filepath = data_path / filename
        if filepath.exists():
            data['students'] = pd.read_csv(filepath)
            print(f"  ✅ {filename} ({len(data['students'])} rows)")
            break
    else:
        data['students'] = pd.DataFrame()
    
    # 기타 파일
    files = {'grades': 'grades.csv', 'volatility': 'volatility.csv', 
             'seteuk': 'seteuk.csv', 'keywords': 'keywords.csv'}
    
    for key, filename in files.items():
        filepath = data_path / filename
        if filepath.exists():
            data[key] = pd.read_csv(filepath)
            print(f"  ✅ {filename} ({len(data[key])} rows)")
        else:
            data[key] = pd.DataFrame()
    
    return data


class Visualizer:
    def __init__(self, output_dir: str = "outputs/figures"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        sns.set_style("whitegrid")
    
    def _get_covid_col(self, df):
        for col in ['has_covid_period', 'has_covid', 'any_covid', 'covid_period']:
            if col in df.columns:
                return col
        return None
    
    def plot_covid_comparison(self, df_students):
        if df_students.empty:
            return
        
        covid_col = self._get_covid_col(df_students)
        if not covid_col:
            return
        
        fig, axes = plt.subplots(1, 2, figsize=(14, 6))
        
        covid_counts = df_students[covid_col].value_counts().sort_index()
        labels = ['비코로나', '코로나'] if len(covid_counts) == 2 else ['코로나']
        axes[0].pie(covid_counts, labels=labels, autopct='%1.1f%%', colors=['#4CAF50', '#F44336'])
        axes[0].set_title('코로나 기간별 학생 분포', fontsize=14, fontweight='bold')
        
        if 'total_remote_days' in df_students.columns:
            remote = df_students[df_students['total_remote_days'] > 0]['total_remote_days']
            if len(remote) > 0:
                sns.histplot(remote, kde=True, ax=axes[1], color='steelblue')
        axes[1].set_title('원격수업일수 분포', fontsize=14, fontweight='bold')
        
        plt.tight_layout()
        plt.savefig(self.output_dir / 'fig1_covid_comparison.png', dpi=150)
        plt.close()
        print("  ✅ fig1_covid_comparison.png")
    
    def plot_volatility(self, df_students, df_volatility):
        if df_students.empty or df_volatility.empty:
            return
        
        covid_col = self._get_covid_col(df_students)
        if not covid_col or 'overall_volatility' not in df_volatility.columns:
            return
        
        id_col = 'anonymous_id' if 'anonymous_id' in df_students.columns else 'student_id'
        merged = df_volatility.merge(df_students[[id_col, covid_col]], 
                                     left_on='student_id', right_on=id_col, how='left')
        merged = merged.dropna(subset=['overall_volatility', covid_col])
        merged['기간'] = merged[covid_col].map({0: '비코로나', 1: '코로나'})
        
        if len(merged) < 4:
            return
        
        fig, ax = plt.subplots(figsize=(10, 6))
        sns.violinplot(data=merged, x='기간', y='overall_volatility', palette=['#4CAF50', '#F44336'])
        ax.set_title('코로나 기간별 성적 변동성', fontsize=14, fontweight='bold')
        
        plt.tight_layout()
        plt.savefig(self.output_dir / 'fig2_volatility.png', dpi=150)
        plt.close()
        print("  ✅ fig2_volatility.png")
    
    def plot_dose_response(self, df_students, df_volatility):
        if df_students.empty or df_volatility.empty:
            return
        
        if 'covid_intensity' not in df_students.columns:
            return
        if 'overall_volatility' not in df_volatility.columns:
            return
        
        id_col = 'anonymous_id' if 'anonymous_id' in df_students.columns else 'student_id'
        merged = df_volatility.merge(df_students[[id_col, 'covid_intensity']], 
                                     left_on='student_id', right_on=id_col, how='left')
        merged = merged.dropna(subset=['overall_volatility', 'covid_intensity'])
        
        if len(merged) < 4:
            return
        
        fig, axes = plt.subplots(1, 3, figsize=(18, 5))
        colors = ['#4CAF50', '#FFC107', '#FF9800', '#F44336']
        
        sns.boxplot(data=merged, x='covid_intensity', y='overall_volatility', palette=colors, ax=axes[0])
        axes[0].set_title('강도별 변동성 분포', fontsize=14, fontweight='bold')
        
        sns.regplot(data=merged, x='covid_intensity', y='overall_volatility', ax=axes[1],
                   scatter_kws={'alpha': 0.5}, line_kws={'color': 'red'})
        axes[1].set_title('선형 회귀 분석', fontsize=14, fontweight='bold')
        
        trend = merged.groupby('covid_intensity')['overall_volatility'].agg(['mean', 'std', 'count']).reset_index()
        trend['se'] = trend['std'] / np.sqrt(trend['count'])
        axes[2].errorbar(trend['covid_intensity'], trend['mean'], yerr=trend['se']*1.96,
                        marker='o', markersize=10, capsize=5, linewidth=2, color='steelblue')
        axes[2].set_title('평균 추세 (95% CI)', fontsize=14, fontweight='bold')
        
        plt.tight_layout()
        plt.savefig(self.output_dir / 'fig3_dose_response.png', dpi=150)
        plt.close()
        print("  ✅ fig3_dose_response.png")
    
    def plot_yearly(self, df_students):
        if df_students.empty:
            return
        
        year_col = None
        for col in ['hs_graduation_year', 'graduation_year', 'grade_year_3']:
            if col in df_students.columns:
                year_col = col
                break
        if not year_col:
            return
        
        yearly = df_students[year_col].dropna().astype(int).value_counts().sort_index()
        if len(yearly) < 2:
            return
        
        fig, ax = plt.subplots(figsize=(12, 6))
        bars = ax.bar(yearly.index, yearly.values, color='steelblue', alpha=0.8)
        for i, (year, _) in enumerate(yearly.items()):
            if 2020 <= year <= 2022:
                bars[i].set_color('#F44336')
        ax.set_title('졸업년도별 분포 (빨간색: 코로나)', fontsize=14, fontweight='bold')
        ax.axvspan(2019.5, 2022.5, alpha=0.1, color='red')
        
        plt.tight_layout()
        plt.savefig(self.output_dir / 'fig4_yearly.png', dpi=150)
        plt.close()
        print("  ✅ fig4_yearly.png")
    
    def plot_grades(self, df_grades):
        if df_grades.empty or 'achievement' not in df_grades.columns:
            return
        
        fig, ax = plt.subplots(figsize=(10, 6))
        counts = df_grades['achievement'].value_counts().sort_index()
        ax.bar(counts.index, counts.values, color='steelblue')
        ax.set_title('전체 등급 분포', fontsize=14, fontweight='bold')
        
        plt.tight_layout()
        plt.savefig(self.output_dir / 'fig5_grades.png', dpi=150)
        plt.close()
        print("  ✅ fig5_grades.png")
    
    def generate_all(self, data):
        print("\n📊 시각화 생성 중...")
        self.plot_covid_comparison(data.get('students', pd.DataFrame()))
        self.plot_volatility(data.get('students', pd.DataFrame()), data.get('volatility', pd.DataFrame()))
        self.plot_dose_response(data.get('students', pd.DataFrame()), data.get('volatility', pd.DataFrame()))
        self.plot_yearly(data.get('students', pd.DataFrame()))
        self.plot_grades(data.get('grades', pd.DataFrame()))
        print(f"\n✅ 저장 완료: {self.output_dir}")


if __name__ == "__main__":
    print("="*60)
    print("📊 STEP 4: 시각화 생성")
    print("="*60)
    
    print("\n📂 데이터 로드...")
    data = load_data()
    
    viz = Visualizer()
    viz.generate_all(data)