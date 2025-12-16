import streamlit as st
import warnings
import pandas as pd
import numpy as np
from datetime import date
from calendar import monthrange
from pandas.tseries.offsets import BDay
import requests

# 忽略警告
warnings.simplefilter('ignore')

# 设置pandas显示选项
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)


class DataLoader:
    """数据处理和加载类"""
    
    def __init__(self):
        """初始化数据加载器"""
        self.headers = {'x-apikey': 'FMNNXJKJMSV6PE4YA36EOAAJXX1WAH84KSWNU8PEUFGRHUPJZA3QTG1FLE09SXJF'}
        self.api_endpoints = {
            'spot': {
                'cape': 'https://api.balticexchange.com/api/v1.3/feed/FDS041FOL8AMWM6CHZEXDRAG9P33TT5W/data',
                'pmx': 'https://api.balticexchange.com/api/v1.3/feed/FDS72H2FOQWJSDTJBVW55HJY1Z6W8ZJ0/data',
                'smx': 'https://api.balticexchange.com/api/v1.3/feed/FDSQZHFHC242QBA1M4OMIW89Q1GBJGCL/data',
                'handy': 'https://api.balticexchange.com/api/v1.3/feed/FDSPMJYK538ET37RIGOY12PFFAXXYUIY/data'
            },
            'route': {
                'cape': 'https://api.balticexchange.com/api/v1.3/feed/FDSIR2LD7ZH28DVT07YZDO77YD4K5T3J/data',
                'pmx': 'https://api.balticexchange.com/api/v1.3/feed/FDSMSBFH191FZVM5NJ4NK51YY6QXCTO7/data',
                'smx': 'https://api.balticexchange.com/api/v1.3/feed/FDSAIN68PQBQM977TO3VCL397UXBVYWV/data',
                'handy': 'https://api.balticexchange.com/api/v1.3/feed/FDSREHV3FRHP773368630ERWCAIU7CX0/data'
            },
            'ffa': {
                'pmx': 'https://api.balticexchange.com/api/v1.3/feed/FDSLG4CKMQ0QEYHE8NJ2DTGR2S6N5S7P/data',
                'cape': 'https://api.balticexchange.com/api/v1.3/feed/FDS2QE6Y0F4LPFOKC4YYVCM38NYVR5DU/data',
                'smx': 'https://api.balticexchange.com/api/v1.3/feed/FDSGGYH6236OC931DOFJ7O4RJ0CK0A8B/data',
                'handy': 'https://api.balticexchange.com/api/v1.3/feed/FDSPIQYIH9UUI56BL6U83DUECJNMQKMW/data'
            }
        }
        self.route_columns = {
            'cape': ['C2', 'C3', 'C5', 'C7', 'C8', 'C9', 'C10', 'C14', 'C16', 'C17'],
            'pmx': ['P1A', 'P2A', 'P3A', 'P4', 'P5', 'P6', 'P7', 'P8'],
            'smx': ['S1B', 'S1C', 'S2', 'S3', 'S4A', 'S4B', 'S5', 'S8', 'S9', 'S10', 'S15'],
            'handy': ['HS1', 'HS2', 'HS3', 'HS4', 'HS5', 'HS6', 'HS7']
        }
    
    def get_date_params(self, business_days=15):
        """获取API调用的日期参数"""
        dateto = pd.to_datetime('today')
        datefrom = dateto - BDay(business_days)
        return {'from': datefrom, 'to': dateto}
    
    def fetch_api_data(self, url, params=None):
        """从API获取数据"""
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return pd.DataFrame(response.json())
        except Exception as e:
            st.error(f"API请求失败: {e}")
            return None


class SpotDataProcessor(DataLoader):
    """现货数据处理类"""
    
    @st.cache_data()
    def load_spot_data(self):
        """加载现货货运数据"""
        st.text('----Getting Spot Freight Data...')
        
        params = self.get_date_params()
        data_frames = {}
        
        # 获取各类船型数据
        for ship_type, url in self.api_endpoints['spot'].items():
            df = self.fetch_api_data(url, params)
            if df is not None and not df.empty:
                temp_df = pd.DataFrame(df.loc[0, 'data'])
                temp_df.set_index('date', inplace=True)
                
                # 重命名列
                column_map = {
                    'cape': 'C5TC',
                    'pmx': 'P4TC',
                    'smx': 'S10TC',
                    'handy': 'HS7TC'
                }
                temp_df.rename(columns={'value': column_map[ship_type]}, inplace=True)
                data_frames[ship_type] = temp_df
        
        # 合并所有数据
        if not data_frames:
            return None
            
        spot_new = data_frames['cape']
        for ship_type in ['pmx', 'smx', 'handy']:
            if ship_type in data_frames:
                spot_new = pd.merge(spot_new, data_frames[ship_type], 
                                  left_index=True, right_index=True, how='outer')
        
        spot_new.index = pd.to_datetime(spot_new.index)
        
        # 读取历史数据并合并
        try:
            spot_old = pd.read_csv('spot.csv')
            spot_old.set_index('Date', inplace=True)
            spot_old.index = pd.to_datetime(spot_old.index)
            
            st.text(f'Spot Data Before Update: {spot_old.index.date[-1]}')
            spot = pd.concat([spot_old, spot_new])
        except FileNotFoundError:
            spot = spot_new
            st.text('No historical spot data found')
        
        # 数据清洗和保存
        spot.reset_index(inplace=True)
        spot.rename(columns={'index': 'Date'}, inplace=True)
        spot = spot.drop_duplicates()
        spot.set_index('Date', inplace=True)
        spot = spot.dropna(subset=['P4TC'])
        
        st.text(f'Spot Data After Update: {spot.index.date[-1]}')
        spot.to_csv('spot.csv', index_label='Date')
        
        return spot


class RouteDataProcessor(DataLoader):
    """路线数据处理类"""
    
    @st.cache_data()
    def load_route_data(self, ship_type):
        """加载路线数据"""
        st.text(f'----Getting {ship_type.capitalize()} Route Data...')
        
        params = self.get_date_params()
        
        # 根据船型设置参数
        config = {
            'cape': {'main_url': self.api_endpoints['spot']['cape'], 'main_col': 'C5TC'},
            'pmx': {'main_url': self.api_endpoints['spot']['pmx'], 'main_col': 'P4TC'},
            'smx': {'main_url': self.api_endpoints['spot']['smx'], 'main_col': 'S10TC'},
            'handy': {'main_url': self.api_endpoints['spot']['handy'], 'main_col': 'HS7TC'}
        }
        
        # 获取主数据
        main_data = self.fetch_api_data(config[ship_type]['main_url'], params)
        if main_data is None or main_data.empty:
            return None
            
        main_df = pd.DataFrame(main_data.loc[0, 'data'])
        main_df.set_index('date', inplace=True)
        main_df.rename(columns={'value': config[ship_type]['main_col']}, inplace=True)
        
        # 获取路线数据
        route_data = self.fetch_api_data(self.api_endpoints['route'][ship_type], params)
        if route_data is None:
            return None
        
        # 合并所有路线数据
        route_df = main_df.copy()
        route_cols = self.route_columns[ship_type]
        
        for i, col_name in enumerate(route_cols):
            if i < len(route_data):
                temp_df = pd.DataFrame(route_data.loc[i, 'data'])
                temp_df.set_index('date', inplace=True)
                temp_df.rename(columns={'value': col_name}, inplace=True)
                route_df = pd.merge(route_df, temp_df, 
                                   left_index=True, right_index=True, how='outer')
        
        route_df.index = pd.to_datetime(route_df.index)
        
        # 读取历史数据并合并
        try:
            filename = f'{ship_type}route.csv'
            route_old = pd.read_csv(filename)
            route_old.set_index('Date', inplace=True)
            route_old.index = pd.to_datetime(route_old.index)
            
            st.text(f'{ship_type.capitalize()} Route Data Before Update: {route_old.index.date[-1]}')
            route_df = pd.concat([route_old, route_df])
        except FileNotFoundError:
            st.text(f'No historical {ship_type} route data found')
        
        # 数据清洗和保存
        route_df.reset_index(inplace=True)
        route_df.rename(columns={'index': 'Date'}, inplace=True)
        route_df = route_df.drop_duplicates(subset='Date', keep='last')
        route_df.set_index('Date', inplace=True)
        
        st.text(f'{ship_type.capitalize()} Route Data After Update: {route_df.index.date[-1]}')
        route_df.to_csv(f'{ship_type}route.csv', index_label='Date')
        
        return route_df


class FFADataProcessor(DataLoader):
    """FFA数据处理类"""
    
    def __init__(self):
        """初始化FFA数据处理器"""
        super().__init__()
        self.month_mapping = {
            'Jan': 'M1', 'Feb': 'M2', 'Mar': 'M3', 'Apr': 'M4', 'May': 'M5', 'Jun': 'M6',
            'Jul': 'M7', 'Aug': 'M8', 'Sep': 'M9', 'Oct': 'M10', 'Nov': 'M11', 'Dec': 'M12',
            'Feb/Mar': 'Q1', 'May/Jun': 'Q2', 'Aug/Sep': 'Q3', 'Nov/Dec': 'Q4', 'Cal': 'Y'
        }
        
        self.ffa_config = {
            'pmx': {
                'columns': ['4TC_PCURMON','4TC_P+1MON','4TC_P+2MON','4TC_P+3MON','4TC_P+4MON','4TC_P+5MON', 
                           '4TC_PCURQ','4TC_P+1Q','4TC_P+2Q','4TC_P+3Q','4TC_P+4Q','4TC_P+5Q',
                           '4TC_P+1CAL','4TC_P+2CAL','4TC_P+3CAL','4TC_P+4CAL','4TC_P+5CAL','4TC_P+6CAL','4TC_P+7CAL'],
                'files': ['p4tc.csv', 'p4tc_r.csv'],
                'spot_col': 'P4TC'
            },
            'cape': {
                'columns': ['5TC_CCURMON','5TC_C+1MON','5TC_C+2MON','5TC_C+3MON','5TC_C+4MON','5TC_C+5MON', 
                           '5TC_CCURQ','5TC_C+1Q','5TC_C+2Q','5TC_C+3Q','5TC_C+4Q','5TC_C+5Q',
                           '5TC_C+1CAL','5TC_C+2CAL','5TC_C+3CAL','5TC_C+4CAL','5TC_C+5CAL','5TC_C+6CAL','5TC_C+7CAL'],
                'files': ['c5tc.csv', 'c5tc_r.csv'],
                'spot_col': 'C5TC'
            },
            'smx': {
                'columns': ['10TC_SCURMON','10TC_S+1MON','10TC_S+2MON','10TC_S+3MON','10TC_S+4MON','10TC_S+5MON', 
                           '10TC_SCURQ','10TC_S+1Q','10TC_S+2Q','10TC_S+3Q','10TC_S+4Q',
                           '10TC_S+1CAL','10TC_S+2CAL','10TC_S+3CAL','10TC_S+4CAL','10TC_S+5CAL','10TC_S+6CAL','10TC_S+7CAL'],
                'files': ['s10tc.csv', 's10tc_r.csv'],
                'spot_col': 'S10TC'
            },
            'handy': {
                'columns': ['TC_H38CURMON','TC_H38+1MON','TC_H38+2MON','TC_H38+3MON','TC_H38+4MON','TC_H38+5MON', 
                           'TC_H38CURQ','TC_H38+1Q','TC_H38+2Q','TC_H38+3Q','TC_H38+4Q',
                           'TC_H38+1CAL','TC_H38+2CAL','TC_H38+3CAL','TC_H38+4CAL','TC_H38+5CAL','TC_H38+6CAL','TC_H38+7CAL'],
                'files': ['hs7tc.csv', 'hs7tc_r.csv'],
                'spot_col': 'HS7TC'
            }
        }
    
    @st.cache_data()
    def load_ffa_data(self, ship_type):
        """加载FFA数据"""
        st.text(f'----Getting {ship_type.upper()} FFA Data...')
        
        params = self.get_date_params()
        url = self.api_endpoints['ffa'][ship_type]
        
        # 获取FFA数据
        ffa_data = self.fetch_api_data(url, params)
        if ffa_data is None or ffa_data.empty:
            return None, None
        
        # 处理FFA数据
        ffa_processed = self._process_ffa_data(ffa_data)
        if ffa_processed is None:
            return None, None
        
        # 创建透视表
        ffa_pt1, ffa_pt2 = self._create_pivot_tables(ffa_processed, ship_type)
        
        # 保存数据
        ffa_final1 = self._save_ffa_data(ffa_pt1, ship_type, 0)
        ffa_final2 = self._save_ffa_data(ffa_pt2, ship_type, 1)
        
        # 合并现货数据
        spot_col = self.ffa_config[ship_type]['spot_col']
        spot_data = st.session_state['spot'][[spot_col]]
        
        if ffa_final1 is not None:
            ffa_final1 = pd.merge(spot_data, ffa_final1, left_index=True, right_index=True, how='outer')
            ffa_final1.dropna(subset=[spot_col], inplace=True)
        
        if ffa_final2 is not None:
            ffa_final2 = pd.merge(spot_data, ffa_final2, left_index=True, right_index=True, how='outer')
            ffa_final2.dropna(subset=[spot_col], inplace=True)
        
        return ffa_final1, ffa_final2
    
    def _process_ffa_data(self, ffa_data):
        """处理原始FFA数据"""
        try:
            ffa_processed = pd.DataFrame()
            for j in range(len(ffa_data.index)):
                date_val = ffa_data.loc[j, 'date']
                groups_df = pd.DataFrame(ffa_data.loc[j, 'groups'])
                
                for i in range(len(groups_df.index)):
                    period_type = groups_df.loc[i, 'periodType']
                    projections_df = pd.DataFrame(groups_df.loc[i, 'projections'])
                    projections_df['periodType'] = period_type
                    projections_df['date'] = date_val
                    ffa_processed = pd.concat([ffa_processed, projections_df])
            
            # 处理月份和年份
            ffa_processed[['Month', 'Year']] = ffa_processed['period'].str.split(' ', expand=True)
            ffa_processed['Month'] = ffa_processed['Month'].replace(self.month_mapping)
            ffa_processed['Contract'] = '20' + ffa_processed['Year'] + '_' + ffa_processed['Month']
            
            return ffa_processed
        except Exception as e:
            st.error(f"处理FFA数据失败: {e}")
            return None
    
    def _create_pivot_tables(self, ffa_processed, ship_type):
        """创建FFA透视表"""
        # 透视表1：按合约分类
        ffa_pt1 = ffa_processed.pivot_table(index='archiveDate', columns='Contract', 
                                           values='value', aggfunc='mean')
        ffa_pt1.index = pd.to_datetime(ffa_pt1.index)
        
        # 透视表2：按路线标识符分类
        ffa_pt2 = ffa_processed.pivot_table(index='archiveDate', columns='identifier', 
                                           values='value', aggfunc='mean')
        ffa_pt2.index = pd.to_datetime(ffa_pt2.index)
        
        # 根据船型筛选特定的列
        if ship_type in self.ffa_config:
            ffa_pt2 = ffa_pt2[self.ffa_config[ship_type]['columns']]
        
        return ffa_pt1, ffa_pt2
    
    def _save_ffa_data(self, ffa_data, ship_type, file_index):
        """保存FFA数据到CSV文件"""
        if ffa_data is None or ffa_data.empty:
            return None
        
        filename = self.ffa_config[ship_type]['files'][file_index]
        
        try:
            ffa_old = pd.read_csv(filename)
            ffa_old.set_index('Date', inplace=True)
            ffa_old.index = pd.to_datetime(ffa_old.index)
            
            if file_index == 0:
                st.text(f'FFA Data Before Update: {ffa_old.index.date[-1]}')
            
            ffa_final = pd.concat([ffa_old, ffa_data])
            ffa_final.reset_index(inplace=True)
            ffa_final.rename(columns={'index': 'Date'}, inplace=True)
            ffa_final = ffa_final.drop_duplicates()
            ffa_final.set_index('Date', inplace=True)
            
            if file_index == 0:
                st.text(f'FFA Data After Update: {ffa_final.index.date[-1]}')
            
            ffa_final.to_csv(filename, index_label='Date')
        except FileNotFoundError:
            ffa_final = ffa_data
            ffa_final.to_csv(filename, index_label='Date')
        
        return ffa_final


class BalticExchangeDashboard:
    """
    波罗的海交易所仪表板主类
    用于获取和处理波罗的海交易所的货运数据和FFA数据
    """
    
    def __init__(self):
        """
        初始化仪表板
        """
        self.spot_processor = SpotDataProcessor()
        self.route_processor = RouteDataProcessor()
        self.ffa_processor = FFADataProcessor()
        
        self.init_ui()
        self.init_session_state()
    
    def init_ui(self):
        """初始化用户界面"""
        st.set_page_config(layout="wide")
        st.title('Baltic Exchange Dashboard')
    
    def init_session_state(self):
        """初始化Streamlit的session_state变量"""
        session_state_keys = [
            'spot', 'caperoute', 'pmxroute', 'smxroute', 'handyroute',
            'p4tc', 'p4tc_r', 'c5tc', 'c5tc_r', 's10tc', 's10tc_r',
            'hs7tc', 'hs7tc_r'
        ]
        
        for key in session_state_keys:
            if key not in st.session_state:
                st.session_state[key] = None
    
    def load_all_data(self):
        """加载所有数据到session_state"""
        st.write('Loading Data...')
        
        # 加载现货数据
        spot_data = self.spot_processor.load_spot_data()
        if spot_data is not None:
            st.session_state['spot'] = spot_data
        
        # 加载各类船型路线数据
        route_types = ['cape', 'pmx', 'smx', 'handy']
        for route_type in route_types:
            route_data = self.route_processor.load_route_data(route_type)
            if route_data is not None:
                st.session_state[f'{route_type}route'] = route_data
        
        # 加载各类船型FFA数据
        ffa_types = ['pmx', 'cape', 'smx', 'handy']
        for ffa_type in ffa_types:
            ffa_data1, ffa_data2 = self.ffa_processor.load_ffa_data(ffa_type)
            if ffa_data1 is not None:
                st.session_state[f'{ffa_type[0]}{ffa_type[1:]}tc'] = ffa_data1
            if ffa_data2 is not None:
                st.session_state[f'{ffa_type[0]}{ffa_type[1:]}tc_r'] = ffa_data2
        
        st.text('Freight Data Done')
        st.write('All Data Loaded!!')
    
    def display_update_button(self):
        """显示数据更新按钮"""
        def update_data():
            """清空缓存和session_state数据"""
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.cache_data.clear()
            st.rerun()
        
        st.button('Update Data', on_click=update_data)
        st.text('数据每12小时自动重新加载以获取潜在更新。')
        st.text('如果您想立即触发重新加载，请点击上面的"Update Data"按钮。')
    
    def run(self):
        """运行仪表板主程序"""
        # 加载所有数据
        self.load_all_data()
        
        # 显示更新按钮
        self.display_update_button()


def main():
    """
    主函数：创建仪表板实例并运行
    """
    # 创建仪表板实例
    dashboard = BalticExchangeDashboard()
    
    # 运行仪表板
    dashboard.run()


if __name__ == "__main__":
    main()
