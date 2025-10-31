/**
 * Watchlist Page
 */
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { WatchlistManager } from '@/components/watchlist/WatchlistManager';
import { AlertManager } from '@/components/watchlist/AlertManager';

export function WatchlistPage() {
  const navigate = useNavigate();
  const [showAlertManager, setShowAlertManager] = useState(false);
  const [selectedSymbol, setSelectedSymbol] = useState<string>('');

  const handleAnalyzeCompany = (symbol: string) => {
    // Navigate to analysis page with pre-selected company
    navigate('/analysis', { state: { preSelectedSymbol: symbol } });
  };

  const handleManageAlerts = (symbol: string) => {
    setSelectedSymbol(symbol);
    setShowAlertManager(true);
  };

  if (showAlertManager) {
    return (
      <AlertManager
        symbol={selectedSymbol}
        onClose={() => setShowAlertManager(false)}
      />
    );
  }

  return (
    <WatchlistManager
      onAnalyzeCompany={handleAnalyzeCompany}
    />
  );
}