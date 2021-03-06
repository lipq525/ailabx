from empyrical import stats
from .common.logging_utils import logger
import numpy as np
import pandas as pd

class Performance(object):
    def __init__(self):
        pass

    def calc_performance(self,df):
        items = ['收益率','年化收益率','波动率','夏普比']

        ret = pd.DataFrame(index=items,columns=df.columns)

        for column in df.columns:
            ret[column] = [
                self.calc_period_return(df[column]),
                self.calc_annual_return(df[column]),
                self.calc_volatility(df[column]),
                self.calc_sharpe(df[column])
            ]
        return ret

    def calc_period_return(self,returns):
        equity = (returns+1).cumprod()
        period_return = equity[-1] - 1
        return period_return

    def calc_annual_return(self,returns):
        period = self.calc_period_return(returns)

        num_years = len(returns) / 252

        return (1+period) ** (1 / num_years) - 1

    def calc_volatility(self,returns):
        return returns.std()*(252 ** 0.5)

    def calc_sharpe(self,returns):
        return (returns.mean() / returns.std()) * (252 ** 0.5)

    def calc_sortino(self,returns):
        return (returns.mean() / returns[returns < 0].std()) * (len(returns) ** 0.5)

    def calc_max_drawdown(self,returns):
        pass
        #return np.std(returns)
    def calc(self,df):
        print('计算绩效')
        df['equity'] = (df['returns'] + 1).cumprod()
        df['bench_equity'] = (df['bench_returns'] + 1).cumprod()

        self.period_return = df['equity'][-1] -1
        self.benchmark_return = df['bench_equity'][-1] -1

        self.trading_days = len(df) #交易天数
        self.annu_return = self.period_return * 252 /self.trading_days
        self.bench_annu_return = self.benchmark_return * 252 / self.trading_days

        # 波动率
        self.volatility = stats.annual_volatility(df['returns'])

        # 夏普比率
        self.sharpe = stats.sharpe_ratio(df['returns'])
        # 最大回撤
        self.max_drawdown = stats.max_drawdown(df['returns'].values)

        #信息比率
       # self.information = stats.information_ratio(df['returns'].values,df['benchmark_returns'].values)

        self.alpha,self.beta = stats.alpha_beta_aligned(df['returns'].values,df['bench_returns'].values)

        return {
            'returns':self.period_return,
            'annu_returns':self.annu_return,
            'bench_returns':self.benchmark_return,
            'bench_annu_returns':self.bench_annu_return,
            'trading_days':self.trading_days,
            'max_drawdown':self.max_drawdown,
            'volatility':self.volatility,
            'sharpe':self.sharpe,
            'alpha':self.alpha,
            'beta':self.beta
        }

from sklearn.ensemble import GradientBoostingClassifier,RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from sklearn.metrics import classification_report
#https://github.com/GenTang/intro_ds
from . import algos
from .consts import *
from datetime import datetime
import os
from .tools import quandl
from .portfolio import Strategy
import yaml
from .technical.indicators import *
from .technical.cross import *


class SymbolRanker(object):
    def split_datasets(self,X,y):
        X_train, X_test, y_train, y_test = train_test_split(X,y,test_size=0.2)
        return (X_train,y_train),(X_test,y_test)

    def train(self,X,y):
        model = GradientBoostingClassifier(random_state=10)
        #model = RandomForestClassifier(random_state=10)

        #划分数据集
        train,test = self.split_datasets(X,y)
        #模型训练
        model.fit(train[0], train[1])

        #模型评估
        print('训练集准确率：',model.score(train[0], train[1]))
        print('测试集准确率：',model.score(test[0],test[1]))
        print(classification_report(model.predict(test[0]), test[1]))

    def predict(self):
        pass


class EventHandler(object):
    def __init__(self):
        self.event_handlers = []
    def reg_handler(self,handler):
        self.event_handlers.append(handler)
    def emit(self,data):
        for handler in self.event_handlers:
            handler(data)

class JobMgr(object):
    def __init__(self):
        self.get_raw_stras()
        ''' 
        self.file = os.path.dirname(os.path.abspath(__file__)) + '/config/stras.yaml'
        if os.path.exists(self.file):
            with open(self.file) as f:
                self.stras = yaml.load(f)
        else:
            self.stras = self.get_raw_stras()
            self.dump_to_file(self.stras)
        '''

    def dump_to_file(self,stras):
        with open(self.file,'w') as f:
            yaml.dump(stras,f)

    def get_stra_by_id(self,id):
        for stra in self.stras:
            if id == stra['job_id']:
                return stra
        return None

    def remove_stra(self,id):
        stra = self.get_stra_by_id(id)
        if stra:
            self.stras.remove(stra)
        self.dump_to_file(self.stras)

    def update_sert_stra(self,stra):
        if self.get_stra_by_id(stra['job_id']) is not None:
            self.remove_stra(stra['job_id'])
        self.stras.append(stra)
        self.dump_to_file(self.stras)
        return True

    def get_raw_stras(self):
        self.stras = [{
            'job_id': '1',
            'name': '海龟策略',
            'desc': '海龟策略',
            'pick_symbols': {
                'market':ShowTypes.market_us,
                'type': ShowTypes.pick_symbol_fixed,
                'universe': ['AAPL', 'AMZN']
            },
            'pick_time': {
                'long': 'cross_up(close,rolling_max(high,20))',
                'flat': 'cross_down(close,rolling_min(low,20))',
            },
            'alloc_funds': ShowTypes.alloc_funds_cash_equally
        },

            {
                'job_id': '2',
                'name': '均线突破',
                'desc': '均线突破',
                'pick_symbols': {
                    'market':ShowTypes.market_btc,
                    'type': ShowTypes.pick_symbol_fixed,
                    'universe': ['AAPL', 'AMZN']
                },
                'pick_time': {
                    'long': 'cross_up(close,ma(close,10))',
                    'flat': 'cross_down(close,ma(close,20))',
                },
                'alloc_funds': ShowTypes.alloc_funds_cash_equally
            },

        ]
        return self.stras



class Backtest(object):
    def __init__(self,name,strategy,data):
        self.name = name
        self.strategy = strategy
        self.data = data
        self.events = None

    def run(self):
        logger.info(self.name + '启动回测引擎...')
        logger.info('共需回测天数:{}'.format(len(self.data.index)))

        self.events.emit({'event_type': EventType.onstart})

        for date in self.data.index:
            self.events.emit({'event_type':EventType.onbar})
            self.strategy.onbar()

    def get_returns(self):
        returns = self.strategy.get_returns()
        returns.name = self.name
        return returns

    def get_equity(self):
        equity = self.strategy.get_equity()
        equity.name = self.name
        return equity

    def get_reports(self):
        return self.strategy.get_reports()


class BacktestRunner(object):
    def __init__(self):
        self.events = EventHandler()
        self.jobmgr = JobMgr()

    def __prepare_data(self,params):
        start_dt = datetime.strptime(params['start'], '%Y-%m-%d')
        end_dt = datetime.strptime(params['end'], '%Y-%m-%d')
        logger.info('回测时间从{}到{}'.format(params['start'],params['end']))

        year = start_dt.year
        year_end = end_dt.year
        years = list(range(year, year_end + 1))

        logger.info('开始准备数据，涉及年份:{}到{}'.format(year,year_end))

        cur_path = os.path.abspath(__file__)
        father_path = os.path.abspath(os.path.dirname(cur_path) + os.path.sep + ".")
        father_path = os.path.abspath(os.path.dirname(father_path) + os.path.sep + ".")

        path = os.path.abspath(father_path + "/data")
        logger.info('数据缓存路径{}'.format(path))

        self.feed = quandl.build_feed("WIKI", params['universe'], years[0], years[-1], path)
        data = quandl.get_close_from_feed(self.feed)

        self.data = data.loc[params['start']:params['end']]

    def parse_stra(self,stra):
        algo_list = []

        sig = pd.DataFrame(index=self.data.index, columns=self.data.columns)

        for symbol in list(self.data.columns):
            close = self.data[symbol]
            high = self.feed[symbol]['High']
            low = self.feed[symbol]['Low']
            sig_long = eval(stra['pick_time']['long'])
            sig_flat = eval(stra['pick_time']['flat'])
            sig[symbol] = sig_long + sig_flat

        algo_list.append(algos.SelectWhere(signal=sig))


        if stra['alloc_funds'] == ShowTypes.alloc_funds_cash_equally:
            algo_list.append(algos.WeighEqually())

        algo_list.append(algos.Rebalance())
        s = Strategy(data=self.data, algos=algo_list)
        e = Backtest(stra['name'], strategy=s, data=self.data.copy())
        return e

    def run_backtests(self,params):
        backtests = []
        self.__prepare_data(params)

        logger.info('自动生成“买入并持有”策略作为基准...')

        # 回测基准
        s = Strategy(data=self.data, algos=[
            algos.RunOnce(),
            algos.SelectAll(),
            algos.WeighEqually(),
            algos.Rebalance()
        ])
        backtests.append(Backtest('基准', strategy=s, data=self.data.copy()))

        for id in params['stras']:
            job = self.jobmgr.get_stra_by_id(id)
            if job is None:
                continue
            engine = self.parse_stra(job)
            backtests.append(engine)


        for backtest in backtests:
            backtest.events = self.events
            backtest.run()

        #收益率曲线
        returns = [b.get_returns() for b in backtests]
        returns = pd.concat(returns,axis=1)


        trades = {}
        for b in backtests:
            reports = b.get_reports()
            reports.dropna(inplace=True)
            trade = reports[reports['trade']!=0]
            cols = list(trade.columns)
            cols.insert(0,'date')
            trade['date'] = trade.index
            trade = trade[cols]
            trade.sort_index(inplace=True)
            trades[b.name] = trade


        #回测结果指标
        ret = Performance().calc_performance(returns)
        ret['指标名称'] = ret.index
        logger.info(ret)

        #equity曲线
        equities = [b.get_equity() for b in backtests]
        equity_df = pd.concat(equities,axis=1)
        equity_df.plot()
        #self.events.emit()

        #df = pd.DataFrame()
        #df.to_dict(orient='records')
        all_data  = {
                          'data':equity_df.to_dict(orient='records'),
                          'performance':ret.to_dict(orient='records'),
                          #'trades':trades,
                          }
        import json
        jsons = json.dumps(all_data,ensure_ascii=False)
        print(jsons)




