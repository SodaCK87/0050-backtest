import pandas as pd
import numpy as np

class BacktestEngine:
    def __init__(self, csv_path, monthly_salary=30000, payday=5, black_swan_threshold=0.2):
        self.csv_path = csv_path
        self.salary = monthly_salary
        self.payday = payday
        self.bs_threshold = black_swan_threshold
        self.fee_rate = 0.001425
        self.tax_rate = 0.001 # ETF Tax 0.1%
        
        # Load and clean standard adjusted CSV
        self.df = pd.read_csv(csv_path)
        self.df['Date'] = pd.to_datetime(self.df['Date'])
        self.df = self.df.sort_values('Date').reset_index(drop=True)
        
        # Pre-calculate Indicators & Paydays (compute once, reuse)
        self._calculate_indicators()
        self._paydays = self._compute_paydays()
    
    def _calculate_indicators(self):
        df = self.df
        # MACD
        exp1 = df['Close'].ewm(span=12, adjust=False).mean()
        exp2 = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = exp1 - exp2
        df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']
        
        # KD (9, 3, 3)
        low_9 = df['Low'].rolling(window=9).min()
        high_9 = df['High'].rolling(window=9).max()
        rsv = 100 * (df['Close'] - low_9) / (high_9 - low_9)
        
        # Manual K, D calculation
        k_values = [50.0]
        d_values = [50.0]
        for i in range(1, len(df)):
            if pd.isna(rsv[i]):
                k_values.append(50.0)
                d_values.append(50.0)
            else:
                new_k = (2/3) * k_values[-1] + (1/3) * rsv[i]
                new_d = (2/3) * d_values[-1] + (1/3) * new_k
                k_values.append(new_k)
                d_values.append(new_d)
        df['K'] = k_values
        df['D'] = d_values
        
        # SMAs
        df['SMA5'] = df['Close'].rolling(window=5).mean()
        df['SMA20'] = df['Close'].rolling(window=20).mean()
        df['SMA60'] = df['Close'].rolling(window=60).mean()

    def run_all(self):
        strategies = [
            ("無腦投入派", self.strategy_no_brainer),
            ("逢低買進派", self.strategy_buy_dip),
            ("動能追高派", self.strategy_momentum),
            ("技術狙擊派", self.strategy_technical),
            ("黑天鵝獵人", self.strategy_black_swan)
        ]
        results = {}
        for name, func in strategies:
            results[name] = func()
        return results

    def _compute_paydays(self):
        """Identify the first trading day on or after the payday of each month. Computed once."""
        paydays = []
        current_month = -1
        paid_this_month = False
        
        for i, row in self.df.iterrows():
            month = row['Date'].month
            if month != current_month:
                current_month = month
                paid_this_month = False
            
            if not paid_this_month and row['Date'].day >= self.payday:
                paydays.append(i)
                paid_this_month = True
        return paydays

    def _get_paydays(self):
        """Return pre-computed paydays."""
        return self._paydays

    def _execute_buy(self, cash, shares, price, amount_to_spend):
        """Calculates fee, buyable shares, and updates balance."""
        if amount_to_spend <= 0:
            return cash, shares
            
        # amount_to_spend = (shares_to_buy * price) * (1 + fee_rate)
        # shares_to_buy = floor(amount_to_spend / (price * (1 + fee_rate)))
        shares_to_buy = int(amount_to_spend // (price * (1 + self.fee_rate)))
        
        if shares_to_buy > 0:
            cost = shares_to_buy * price
            fee = cost * self.fee_rate
            total_cost = cost + fee
            if total_cost <= cash:
                cash -= total_cost
                shares += shares_to_buy
        return cash, shares

    def calculate_metrics(self, equity_curve, cash_curve, total_invested):
        equity = np.array(equity_curve)
        # ROI: based on actual total capital invested, not estimated from paydays
        roi = ((equity[-1] - total_invested) / total_invested * 100) if total_invested > 0 else 0.0
        # MDD
        peak = np.maximum.accumulate(equity)
        # Avoid division by zero on flat equity (all cash, no activity)
        with np.errstate(invalid='ignore', divide='ignore'):
            drawdown = np.where(peak > 0, (equity - peak) / peak, 0)
        mdd = float(np.min(drawdown) * 100)
        # Stress Index (|MDD| amplified by volatility)
        with np.errstate(divide='ignore', invalid='ignore'):
            daily_returns = np.diff(equity) / np.where(equity[:-1] == 0, np.nan, equity[:-1]) if len(equity) > 1 else np.array([0.0])
        vol = float(np.nanstd(daily_returns))
        stress_index = abs(mdd) * (1 + vol * 10)
        # Cash Drag: average fraction of portfolio sitting as uninvested cash
        mean_equity = np.mean(equity)
        cash_drag = (np.mean(cash_curve) / mean_equity * 100) if mean_equity > 0 else 100.0
        
        return {
            "ROI": roi,
            "MDD": mdd,
            "Stress": stress_index,
            "CashDrag": cash_drag,
            "TotalInvested": total_invested
        }

    def strategy_no_brainer(self):
        cash = 0
        shares = 0
        total_invested = 0
        paydays = self._get_paydays()
        paydays_set = set(paydays)
        equity_curve = []
        shares_curve = []
        cash_curve = []
        
        for i, row in self.df.iterrows():
            if i in paydays_set:
                cash += self.salary
                total_invested += self.salary
                cash, shares = self._execute_buy(cash, shares, row['Close'], cash)
            
            equity = cash + shares * row['Close']
            equity_curve.append(equity)
            shares_curve.append(shares)
            cash_curve.append(cash)
            
        return {"equity": equity_curve, "shares": shares_curve, "cash": cash_curve, "metrics": self.calculate_metrics(equity_curve, cash_curve, total_invested)}

    def strategy_buy_dip(self):
        cash = 0
        shares = 0
        total_invested = 0
        paydays = self._get_paydays()
        paydays_set = set(paydays)
        pending_half = 0  # Accumulates across months if signal never fires
        equity_curve = []
        shares_curve = []
        cash_curve = []
        
        for i, row in self.df.iterrows():
            if i in paydays_set:
                cash += self.salary
                total_invested += self.salary
                # Buy 50% immediately
                amount = self.salary * 0.5
                cash, shares = self._execute_buy(cash, shares, row['Close'], amount)
                # FIX Bug 4: += to accumulate, not overwrite previous month's unspent half
                pending_half += self.salary * 0.5
            
            # Check for "Down Day" (Close < Open) for the pending amount
            if pending_half > 0:
                if row['Close'] < row['Open']:
                    cash, shares = self._execute_buy(cash, shares, row['Close'], pending_half)
                    pending_half = 0
                elif i + 1 < len(self.df) and self.df.iloc[i+1]['Date'].month != row['Date'].month:
                    # Last day of month, buy anyway
                    cash, shares = self._execute_buy(cash, shares, row['Close'], pending_half)
                    pending_half = 0
                    
            equity = cash + shares * row['Close']
            equity_curve.append(equity)
            shares_curve.append(shares)
            cash_curve.append(cash)
            
        return {"equity": equity_curve, "shares": shares_curve, "cash": cash_curve, "metrics": self.calculate_metrics(equity_curve, cash_curve, total_invested)}

    def strategy_momentum(self):
        cash = 0
        shares = 0
        total_invested = 0
        paydays = self._get_paydays()
        paydays_set = set(paydays)
        pending_half = 0  # Accumulates across months if signal never fires
        equity_curve = []
        shares_curve = []
        cash_curve = []
        
        for i, row in self.df.iterrows():
            if i in paydays_set:
                cash += self.salary
                total_invested += self.salary
                amount = self.salary * 0.5
                cash, shares = self._execute_buy(cash, shares, row['Close'], amount)
                # FIX Bug 4: += to accumulate, not overwrite previous month's unspent half
                pending_half += self.salary * 0.5
            
            # FIX Bug 1: Need i >= 3 for a true 3-consecutive-day check (4 data points)
            if pending_half > 0:
                if i >= 3:
                    if (self.df.iloc[i]['Close'] > self.df.iloc[i-1]['Close'] and 
                        self.df.iloc[i-1]['Close'] > self.df.iloc[i-2]['Close'] and
                        self.df.iloc[i-2]['Close'] > self.df.iloc[i-3]['Close']):
                        cash, shares = self._execute_buy(cash, shares, row['Close'], pending_half)
                        pending_half = 0
                
                if pending_half > 0 and (i + 1 < len(self.df) and self.df.iloc[i+1]['Date'].month != row['Date'].month):
                    cash, shares = self._execute_buy(cash, shares, row['Close'], pending_half)
                    pending_half = 0

            equity = cash + shares * row['Close']
            equity_curve.append(equity)
            shares_curve.append(shares)
            cash_curve.append(cash)
            
        return {"equity": equity_curve, "shares": shares_curve, "cash": cash_curve, "metrics": self.calculate_metrics(equity_curve, cash_curve, total_invested)}

    def strategy_technical(self):
        cash = 0
        shares = 0
        total_invested = 0
        paydays = self._get_paydays()
        paydays_set = set(paydays)
        equity_curve = []
        shares_curve = []
        cash_curve = []
        
        for i, row in self.df.iterrows():
            if i in paydays_set:
                cash += self.salary
                total_invested += self.salary
            
            # FIX: Original condition (MACD cross 0 AND KD < 30 simultaneously) was too strict 
            # because MACD lags significantly behind KD. 
            # New Logic: Trigger on EITHER a KD golden cross in the low/mid zone (early reversal) 
            # OR a MACD histogram zero-crossover (trend confirmation).
            if i > 0:
                prev = self.df.iloc[i-1]
                
                kd_golden_cross = (row['K'] > row['D']) and (prev['K'] <= prev['D']) and (row['K'] < 50)
                macd_zero_cross = (row['MACD_Hist'] > 0) and (prev['MACD_Hist'] <= 0)
                
                if kd_golden_cross or macd_zero_cross:
                    # Deploy 20% of current cash per signal (up to 5 tranches)
                    amount = cash * 0.2
                    cash, shares = self._execute_buy(cash, shares, row['Close'], amount)

            equity = cash + shares * row['Close']
            equity_curve.append(equity)
            shares_curve.append(shares)
            cash_curve.append(cash)
            
        return {"equity": equity_curve, "shares": shares_curve, "cash": cash_curve, "metrics": self.calculate_metrics(equity_curve, cash_curve, total_invested)}

    def strategy_black_swan(self):
        cash = 0 
        shares = 0
        short_term_shares = 0
        total_invested = 0
        paydays = self._get_paydays()
        paydays_set = set(paydays)
        equity_curve = []
        shares_curve = []
        cash_curve = []
        hist_peak = 0
        
        for i, row in self.df.iterrows():
            if i in paydays_set:
                cash += self.salary
                total_invested += self.salary
            
            hist_peak = max(hist_peak, row['Close'])
            
            # Big Dip logic: all-in when price drops X% from historical peak
            if row['Close'] <= hist_peak * (1 - self.bs_threshold):
                cash, shares = self._execute_buy(cash, shares, row['Close'], cash)
            
            # FIX Bug 3: Guard i > 0 and check NaN before SMA crossover comparison
            # Short term pool: 15% of cash, trade on SMA5/SMA20 crossover
            if i > 0:
                prev = self.df.iloc[i-1]
                sma5_ok = pd.notna(row['SMA5']) and pd.notna(prev['SMA5'])
                sma20_ok = pd.notna(row['SMA20']) and pd.notna(prev['SMA20'])
                
                if sma5_ok and sma20_ok:
                    # Golden cross: SMA5 crosses above SMA20
                    if row['SMA5'] > row['SMA20'] and prev['SMA5'] <= prev['SMA20']:
                        amount = cash * 0.15
                        cash, short_term_shares = self._execute_buy(cash, short_term_shares, row['Close'], amount)
                    # Death cross: SMA5 crosses below SMA20 — sell all short-term
                    elif row['SMA5'] < row['SMA20'] and prev['SMA5'] >= prev['SMA20']:
                        if short_term_shares > 0:
                            sell_value = short_term_shares * row['Close']
                            sell_fee = sell_value * self.fee_rate
                            sell_tax = sell_value * self.tax_rate
                            cash += (sell_value - sell_fee - sell_tax)
                            short_term_shares = 0

            equity = cash + (shares + short_term_shares) * row['Close']
            equity_curve.append(equity)
            equity_curve_shares = shares + short_term_shares
            shares_curve.append(equity_curve_shares)
            cash_curve.append(cash)
            
        return {"equity": equity_curve, "shares": shares_curve, "cash": cash_curve, "metrics": self.calculate_metrics(equity_curve, cash_curve, total_invested)}
