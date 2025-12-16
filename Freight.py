# baltic_dashboard.py
import streamlit as st
import warnings, pandas as pd, numpy as np, requests
from datetime import date
from calendar import monthrange
from pandas.tseries.offsets import BDay

warnings.simplefilter("ignore")
pd.set_option("display.max_rows", None)
pd.set_option("display.max_columns", None)

# -------------------- 核心类 --------------------
class BalticDashboard:
    API_KEY = "FMNNXJKJMSV6PE4YA36EOAAJXX1WAH84KSWNU8PEUFGRHUPJZA3QTG1FLE09SXJF"

    def __init__(self):
        self.headers = {"x-apikey": self.API_KEY}
        self.spot = None
        self.caperoute = None
        self.pmxroute = None
        self.smxroute = None
        self.handyroute = None
        self.p4tc, self.p4tc_r = None, None
        self.c5tc, self.c5tc_r = None, None
        self.s10tc, self.s10tc_r = None, None
        self.hs7tc, self.hs7tc_r = None, None

    # -------------------- 工具方法 --------------------
    @staticmethod
    def _today():
        return pd.to_datetime(date.today())

    @staticmethod
    def _bday_ago(n):
        return BalticDashboard._today() - BDay(n)

    def _get(self, url, params=None):
        """统一带 header 的 GET"""
        return requests.get(url.strip(), headers=self.headers, params=params or {})

    # -------------------- 数据加载 --------------------
    @st.cache_data
    def load_spot_data(_self):
        """Spot 主指数：C5TC / P4TC / S10TC / HS7TC"""
        st.text("----Getting Freight Data...")
        dateto, datefrom = _self._today(), _self._bday_ago(15)
        params = {"from": datefrom, "to": dateto}

        urls = {
            "C5TC": "https://api.balticexchange.com/api/v1.3/feed/FDS041FOL8AMWM6CHZEXDRAG9P33TT5W/data",
            "P4TC": "https://api.balticexchange.com/api/v1.3/feed/FDS72H2FOQWJSDTJBVW55HJY1Z6W8ZJ0/data",
            "S10TC": "https://api.balticexchange.com/api/v1.3/feed/FDSQZHFHC242QBA1M4OMIW89Q1GBJGCL/data",
            "HS7TC": "https://api.balticexchange.com/api/v1.3/feed/FDSPMJYK538ET37RIGOY12PFFAXXYUIY/data",
        }

        def fetch(route):
            return pd.DataFrame(_self._get(urls[route], params).json().loc[0, "data"])

        spotnew = (
            fetch("C5TC").set_index("date").rename(columns={"value": "C5TC"})
            .join(fetch("P4TC").set_index("date").rename(columns={"value": "P4TC"}), how="outer")
            .join(fetch("S10TC").set_index("date").rename(columns={"value": "S10TC"}), how="outer")
            .join(fetch("HS7TC").set_index("date").rename(columns={"value": "HS7TC"}), how="outer")
        )
        spotnew.index = pd.to_datetime(spotnew.index)

        spotold = pd.read_csv("spot.csv", index_col="Date", parse_dates=True)
        st.text(f"Spot Data Before Update: {spotold.index.date[-1]}")
        spot = (
            pd.concat([spotold, spotnew])
            .reset_index()
            .drop_duplicates()
            .set_index("Date")
            .dropna(subset=["P4TC"])
        )
        st.text(f"Spot Data After Update: {spot.index.date[-1]}")
        spot.to_csv("spot.csv", index_label="Date")
        return spot

    @st.cache_data
    def load_caperoute_data(_self):
        return _self._load_route("cape", "caperoute.csv")

    @st.cache_data
    def load_pmxroute_data(_self):
        return _self._load_route("pmx", "pmxroute.csv")

    @st.cache_data
    def load_smxroute_data(_self):
        return _self._load_route("smx", "smxroute.csv")

    @st.cache_data
    def load_handyroute_data(_self):
        return _self._load_route("handy", "handyroute.csv")

    # ---- 通用 route 抓取 ----
    def _load_route(self, ship_type: str, csv_file: str):
        dateto, datefrom = self._today(), self._bday_ago(15)
        params = {"from": datefrom, "to": dateto}

        # 主指数
        main_url = {
            "cape": "https://api.balticexchange.com/api/v1.3/feed/FDS041FOL8AMWM6CHZEXDRAG9P33TT5W/data",
            "pmx": "https://api.balticexchange.com/api/v1.3/feed/FDS72H2FOQWJSDTJBVW55HJY1Z6W8ZJ0/data",
            "smx": "https://api.balticexchange.com/api/v1.3/feed/FDSQZHFHC242QBA1M4OMIW89Q1GBJGCL/data",
            "handy": "https://api.balticexchange.com/api/v1.3/feed/FDSPMJYK538ET37RIGOY12PFFAXXYUIY/data",
        }[ship_type]

        route_url = {
            "cape": "https://api.balticexchange.com/api/v1.3/feed/FDSIR2LD7ZH28DVT07YZDO77YD4K5T3J/data",
            "pmx": "https://api.balticexchange.com/api/v1.3/feed/FDSMSBFH191FZVM5NJ4NK51YY6QXCTO7/data",
            "smx": "https://api.balticexchange.com/api/v1.3/feed/FDSAIN68PQBQM977TO3VCL397UXBVYWV/data",
            "handy": "https://api.balticexchange.com/api/v1.3/feed/FDSREHV3FRHP773368630ERWCAIU7CX0/data",
        }[ship_type]

        main = pd.DataFrame(self._get(main_url, params).json().loc[0, "data"]).set_index("date").rename(columns={"value": ship_type.upper() + "TC"})
        route_json = self._get(route_url, params).json()

        df = main
        for idx, row in route_json.iterrows():
            code = row["code"]  # 如 C2, P1A, S1B...
            tmp = pd.DataFrame(row["data"]).set_index("date").rename(columns={"value": code})
            df = df.join(tmp, how="outer")

        df.index = pd.to_datetime(df.index)
        old = pd.read_csv(csv_file, index_col="Date", parse_dates=True)
        st.text(f"{ship_type.capitalize()} Route Data Before Update: {old.index.date[-1]}")
        new = (
            pd.concat([old, df])
            .reset_index()
            .drop_duplicates(subset="Date", keep="last")
            .set_index("Date")
        )
        st.text(f"{ship_type.capitalize()} Route Data After Update: {new.index.date[-1]}")
        new.to_csv(csv_file, index_label="Date")
        return new

    # -------------------- FFA 通用 --------------------
    def _load_ffa(self, ffa_url: str, spot_col: str, csv_stub: str):
        dateto, datefrom = self._today(), self._bday_ago(15)
        params = {"from": datefrom, "to": dateto}

        raw = pd.DataFrame(self._get(ffa_url, params).json().loc[0, "groupings"])
        records = []
        for _, day_row in raw.iterrows():
            dt = day_row["date"]
            for _, grp in pd.DataFrame(day_row["groups"]).iterrows():
                period = grp["periodType"]
                for _, proj in pd.DataFrame(grp["projections"]).iterrows():
                    records.append(
                        {
                            "archiveDate": dt,
                            "period": proj["period"],
                            "identifier": proj["identifier"],
                            "value": proj["value"],
                            "periodType": period,
                        }
                    )
        df = pd.DataFrame(records)
        df[["Month", "Year"]] = df["period"].str.split(" ", expand=True)
        month_map = {
            "Jan": "M1", "Feb": "M2", "Mar": "M3", "Apr": "M4", "May": "M5", "Jun": "M6",
            "Jul": "M7", "Aug": "M8", "Sep": "M9", "Oct": "M10", "Nov": "M11", "Dec": "M12",
            "Feb/Mar": "Q1", "May/Jun": "Q2", "Aug/Sep": "Q3", "Nov/Dec": "Q4", "Cal": "Y",
        }
        df["Month"] = df["Month"].map(month_map)
        df["Contract"] = "20" + df["Year"] + "_" + df["Month"]

        pt1 = df.pivot_table(index="archiveDate", columns="Contract", values="value", aggfunc="mean")
        pt1.index = pd.to_datetime(pt1.index)

        old1 = pd.read_csv(f"{csv_stub}.csv", index_col="Date", parse_dates=True)
        st.text(f"FFA Data Before Update: {old1.index.date[-1]}")
        new1 = pd.concat([old1, pt1]).reset_index().drop_duplicates().set_index("Date")
        st.text(f"FFA Data After Update: {new1.index.date[-1]}")
        new1.to_csv(f"{csv_stub}.csv", index_label="Date")

        pt2 = df.pivot_table(index="archiveDate", columns="identifier", values="value", aggfunc="mean")
        pt2.index = pd.to_datetime(pt2.index)
        old2 = pd.read_csv(f"{csv_stub}_r.csv", index_col="Date", parse_dates=True)
        new2 = pd.concat([old2, pt2]).reset_index().drop_duplicates().set_index("Date")
        new2.to_csv(f"{csv_stub}_r.csv", index_label="Date")

        spot = st.session_state["spot"][[spot_col]]
        merged1 = pd.merge(spot, new1, left_index=True, right_index=True, how="outer").dropna(subset=[spot_col])
        merged2 = pd.merge(spot, new2, left_index=True, right_index=True, how="outer").dropna(subset=[spot_col])
        return merged1, merged2

    # ---- 四个船型 FFA 入口 ----
    def load_pmx_ffa_data(self):
        url = "https://api.balticexchange.com/api/v1.3/feed/FDSLG4CKMQ0QEYHE8NJ2DTGR2S6N5S7P/data"
        return self._load_ffa(url, "P4TC", "p4tc")

    def load_cape_ffa_data(self):
        url = "https://api.balticexchange.com/api/v1.3/feed/FDS2QE6Y0F4LPFOKC4YYVCM38NYVR5DU/data"
        return self._load_ffa(url, "C5TC", "c5tc")

    def load_smx_ffa_data(self):
        url = "https://api.balticexchange.com/api/v1.3/feed/FDSGGYH6236OC931DOFJ7O4RJ0CK0A8B/data"
        return self._load_ffa(url, "S10TC", "s10tc")

    def load_handy_ffa_data(self):
        url = "https://api.balticexchange.com/api/v1.3/feed/FDSPIQYIH9UUI56BL6U83DUECJNMQKMW/data"
        return self._load_ffa(url, "HS7TC", "hs7tc")

    # -------------------- 统一跑批 --------------------
    def run(self):
        st.title("Baltic Exchange Dashboard")
        st.write("Loading Data...")

        # 1. spot
        self.spot = self.load_spot_data()
        st.session_state["spot"] = self.spot

        # 2. routes
        self.caperoute = self.load_caperoute_data()
        self.pmxroute = self.load_pmxroute_data()
        self.smxroute = self.load_smxroute_data()
        self.handyroute = self.load_handyroute_data()
        for k, v in {
            "caperoute": self.caperoute,
            "pmxroute": self.pmxroute,
            "smxroute": self.smxroute,
            "handyroute": self.handyroute,
        }.items():
            st.session_state[k] = v

        # 3. ffa
        self.p4tc, self.p4tc_r = self.load_pmx_ffa_data()
        self.c5tc, self.c5tc_r = self.load_cape_ffa_data()
        self.s10tc, self.s10tc_r = self.load_smx_ffa_data()
        self.hs7tc, self.hs7tc_r = self.load_handy_ffa_data()
        for k, v in {
            "p4tc": self.p4tc,
            "p4tc_r": self.p4tc_r,
            "c5tc": self.c5tc,
            "c5tc_r": self.c5tc_r,
            "s10tc": self.s10tc,
            "s10tc_r": self.s10tc_r,
            "hs7tc": self.hs7tc,
            "hs7tc_r": self.hs7tc_r,
        }.items():
            st.session_state[k] = v

        st.text("Freight Data Done")
        st.write("All Data Loaded!!")

        # 手动刷新按钮
        def update():
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.cache_data.clear()

        st.button("Update Data", on_click=update)
        st.text("Data is automatically reloaded for potential updates every 12 hours.")
        st.text('If you would like to trigger the reload right now, please click on the above "Update Data" button.')


# -------------------- 入口 --------------------
if __name__ == "__main__":
    dash = BalticDashboard()
    dash.run()