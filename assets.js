export const CATEGORY_META = {
  forex: {
    title: 'Forex',
    subtitle: 'Валютные пары',
    short: 'FX',
    tone: 'from-emerald-400/20 to-cyan-400/10'
  },
  crypto: {
    title: 'Крипто',
    subtitle: 'Цифровые активы',
    short: 'CR',
    tone: 'from-sky-400/20 to-emerald-400/10'
  },
  stocks: {
    title: 'Акции',
    subtitle: 'Компании США',
    short: 'ST',
    tone: 'from-violet-400/20 to-emerald-400/10'
  },
  indices: {
    title: 'Индексы',
    subtitle: 'Мировые рынки',
    short: 'IX',
    tone: 'from-amber-300/20 to-emerald-400/10'
  },
  commodities: {
    title: 'Сырьё',
    subtitle: 'Металлы и энергия',
    short: 'CM',
    tone: 'from-rose-300/20 to-emerald-400/10'
  }
};

export const ASSETS = {
  forex: [
    'EUR/USD', 'GBP/USD', 'USD/JPY', 'AUD/USD', 'NZD/USD', 'USD/CAD',
    'USD/CHF', 'EUR/GBP', 'EUR/JPY', 'EUR/CHF', 'EUR/NZD', 'EUR/HUF',
    'EUR/TRY', 'EUR/RUB', 'GBP/JPY', 'GBP/AUD', 'AUD/JPY', 'AUD/CAD',
    'AUD/CHF', 'AUD/NZD', 'CAD/JPY', 'CAD/CHF', 'CHF/JPY', 'CHF/NOK',
    'NZD/JPY', 'USD/BRL', 'USD/RUB', 'USD/MXN', 'USD/CNH', 'USD/SGD',
    'USD/INR', 'USD/PKR', 'USD/IDR', 'USD/BDT', 'USD/PHP', 'USD/THB',
    'USD/VND', 'USD/MYR', 'USD/COP', 'USD/ARS', 'USD/CLP', 'USD/EGP',
    'USD/DZD', 'MAD/USD', 'BHD/CNY', 'AED/CNY', 'KES/USD', 'ZAR/USD',
    'UAH/USD', 'NGN/USD', 'LBP/USD', 'JOD/CNY', 'SAR/CNY', 'OMR/CNY',
    'QAR/CNY'
  ],
  crypto: [
    'BTC/USD', 'ETH/USD', 'BNB/USD', 'SOL/USD', 'ADA/USD', 'DOT/USD',
    'DOGE/USD', 'LTC/USD', 'LINK/USD', 'AVAX/USD', 'MATIC/USD', 'TRX/USD',
    'TON/USD', 'XRP/USD'
  ],
  commodities: ['XAU/USD', 'XAG/USD', 'BRENT', 'WTI', 'NGAS', 'PLAT', 'PALL'],
  stocks: [
    'NVDA', 'AAPL', 'MSFT', 'AMZN', 'TSLA', 'META', 'NFLX', 'GOOGL',
    'AMD', 'INTC', 'V', 'C', 'XOM', 'BA', 'MCD', 'PFE', 'JNJ',
    'BABA', 'CSCO', 'AXP', 'FDX', 'GME', 'PLTR', 'MARA', 'COIN'
  ],
  indices: ['SP500', 'US100', 'DJI30', 'D30EUR', 'F40EUR', 'E35EUR', 'E50EUR', '100GBP', 'JPN225', 'AUS200', 'VIX']
};

export const CATEGORY_ORDER = ['forex', 'crypto', 'stocks', 'indices', 'commodities'];

