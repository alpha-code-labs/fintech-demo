import { useEffect, useRef, memo } from 'react';

/**
 * TradingView Advanced Chart widget for NSE stocks.
 * Uses the free TradingView widget embed (no API key needed).
 */
function TradingViewChart({ symbol, height = 400 }) {
  const containerRef = useRef(null);

  useEffect(() => {
    if (!containerRef.current) return;

    // Clear previous widget
    containerRef.current.innerHTML = '';

    const script = document.createElement('script');
    script.src = 'https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js';
    script.type = 'text/javascript';
    script.async = true;
    script.innerHTML = JSON.stringify({
      autosize: true,
      symbol: `NSE:${symbol}`,
      interval: 'W',
      timezone: 'Asia/Kolkata',
      theme: 'dark',
      style: '1',
      locale: 'en',
      backgroundColor: 'rgba(19, 23, 34, 1)',
      gridColor: 'rgba(255, 255, 255, 0.04)',
      hide_top_toolbar: false,
      hide_legend: false,
      allow_symbol_change: false,
      save_image: false,
      calendar: false,
      hide_volume: false,
      support_host: 'https://www.tradingview.com',
      studies: [
        { id: 'MASimple@tv-basicstudies', inputs: { length: 10 } },
        { id: 'MASimple@tv-basicstudies', inputs: { length: 30 } },
        { id: 'MASimple@tv-basicstudies', inputs: { length: 52 } },
      ],
    });

    containerRef.current.appendChild(script);

    return () => {
      if (containerRef.current) {
        containerRef.current.innerHTML = '';
      }
    };
  }, [symbol]);

  return (
    <div
      className="tradingview-widget-container"
      ref={containerRef}
      style={{ height, width: '100%' }}
    />
  );
}

export default memo(TradingViewChart);
