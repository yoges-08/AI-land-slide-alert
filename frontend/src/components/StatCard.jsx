import React, { useState, useEffect, useRef } from 'react';
import { TrendingUp, TrendingDown, MapPin, AlertTriangle, AlertCircle, ShieldCheck, Clock } from 'lucide-react';

/**
 * useCountUp Hook - Animates numbers counting up from 0 with easeOutQuad easing
 */
export function useCountUp(endValue, duration = 1800) {
  const [displayValue, setDisplayValue] = useState(0);

  useEffect(() => {
    // If endValue is not a number, handle non-numeric or suffix cases
    const numericStr = String(endValue).replace(/[^0-9.-]/g, '');
    const target = parseFloat(numericStr);
    
    if (isNaN(target)) {
      setDisplayValue(endValue);
      return;
    }

    // Detect if original had decimals
    const hasDecimals = String(endValue).includes('.') && String(endValue).split('.')[1]?.length > 0;
    const decimalPlaces = hasDecimals ? Math.min(2, String(endValue).split('.')[1].length) : 0;
    const suffix = String(endValue).replace(/[0-9.-]/g, '');

    let startTime = null;
    let animationFrameId;

    const animate = (timestamp) => {
      if (!startTime) startTime = timestamp;
      const progress = Math.min((timestamp - startTime) / duration, 1);
      
      // easeOutQuad easing: t * (2 - t)
      const easedProgress = progress * (2 - progress);
      const currentVal = target * easedProgress;

      const formatted = decimalPlaces > 0
        ? currentVal.toFixed(decimalPlaces)
        : Math.round(currentVal);

      setDisplayValue(`${formatted}${suffix}`);

      if (progress < 1) {
        animationFrameId = requestAnimationFrame(animate);
      } else {
        setDisplayValue(endValue);
      }
    };

    animationFrameId = requestAnimationFrame(animate);

    return () => {
      if (animationFrameId) cancelAnimationFrame(animationFrameId);
    };
  }, [endValue, duration]);

  return displayValue;
}

export default function StatCard({
  title,
  value,
  change,
  changeType = 'up',
  subtitle,
  type = 'total', // 'total' | 'high' | 'moderate' | 'low'
  onClick
}) {
  const animatedValue = useCountUp(value, 1600);
  const [secondsAgo, setSecondsAgo] = useState(1);

  // Live second ticker
  useEffect(() => {
    setSecondsAgo(1);
    const interval = setInterval(() => {
      setSecondsAgo((prev) => prev + 1);
    }, 1000);
    return () => clearInterval(interval);
  }, [value]);

  let iconBg = 'bg-emerald-50 text-emerald-600 border-emerald-200';
  let Icon = MapPin;
  let changeColor = 'text-emerald-600';
  let glowBorder = 'hover:border-emerald-300 hover:shadow-emerald-500/10';

  if (type === 'high') {
    iconBg = 'bg-red-50 text-red-600 border-red-200';
    Icon = AlertTriangle;
    changeColor = 'text-red-500';
    glowBorder = 'hover:border-red-300 hover:shadow-red-500/10';
  } else if (type === 'moderate') {
    iconBg = 'bg-amber-50 text-amber-600 border-amber-200';
    Icon = AlertCircle;
    changeColor = 'text-amber-500';
    glowBorder = 'hover:border-amber-300 hover:shadow-amber-500/10';
  } else if (type === 'low') {
    iconBg = 'bg-emerald-50 text-emerald-600 border-emerald-200';
    Icon = ShieldCheck;
    changeColor = 'text-emerald-600';
    glowBorder = 'hover:border-emerald-300 hover:shadow-emerald-500/10';
  }

  return (
    <div
      onClick={onClick}
      className={`group relative bg-white rounded-2xl p-4 border border-slate-200/90 shadow-sm flex flex-col justify-between transition-all duration-300 transform hover:scale-[1.02] hover:shadow-md ${glowBorder} ${
        onClick ? 'cursor-pointer' : ''
      }`}
    >
      <div className="flex items-start space-x-3.5">
        <div className={`p-2.5 rounded-xl border flex items-center justify-center flex-shrink-0 transition-transform group-hover:scale-110 ${iconBg}`}>
          <Icon className="w-5 h-5 stroke-[2.2]" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-[11px] font-semibold text-slate-500 truncate leading-none mb-1.5">{title}</p>
          <div className="flex items-baseline space-x-2">
            <span className="text-2xl font-black text-slate-900 tracking-tight leading-none">
              {animatedValue}
            </span>
            {change && (
              <span className={`text-[11px] font-bold flex items-center space-x-0.5 ${changeColor}`}>
                {changeType === 'up' ? '↑' : '↓'} {change}
              </span>
            )}
          </div>
          {subtitle && (
            <p className="text-[10px] text-slate-400 mt-1 truncate leading-none">{subtitle}</p>
          )}
        </div>
      </div>

      {/* Live Second Ticker Badge */}
      <div className="mt-3 pt-2 border-t border-slate-100 flex items-center justify-between text-[9px] text-slate-400">
        <div className="flex items-center space-x-1">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-ping" />
          <span className="font-medium text-slate-500">Live stream</span>
        </div>
        <span className="font-mono">Updated {secondsAgo}s ago</span>
      </div>
    </div>
  );
}
