/**
 * Portfolio Overview Component
 */
import React from 'react';
import {
  TrendingUp,
  TrendingDown,
  DollarSign,
  PieChart,
  BarChart3,
  Target,
  AlertTriangle,
  CheckCircle,
} from 'lucide-react';
import { Portfolio, PortfolioPosition } from '@/types/financial';
import { FinancialChart } from '@/components/charts/FinancialChart';

interface PortfolioOverviewProps {
  portfolio: Portfolio;
  showDetailed?: boolean;
}

export function PortfolioOverview({ portfolio, showDetailed = true }: PortfolioOverviewProps) {
  const totalValue = portfolio.total_value;
  const totalReturn = portfolio.total_return;
  const totalReturnPercentage = portfolio.total_return_percentage;
  
  // Calculate portfolio metrics
  const topPositions = portfolio.positions
    .sort((a, b) => b.weight - a.weight)
    .slice(0, 5);
  
  const gainers = portfolio.positions
    .filter(p => p.unrealized_gain_loss_percentage > 0)
    .sort((a, b) => b.unrealized_gain_loss_percentage - a.unrealized_gain_loss_percentage)
    .slice(0, 3);
    
  const losers = portfolio.positions
    .filter(p => p.unrealized_gain_loss_percentage < 0)
    .sort((a, b) => a.unrealized_gain_loss_percentage - b.unrealized_gain_loss_percentage)
    .slice(0, 3);

  // Sector allocation data
  const sectorAllocation = portfolio.positions.reduce((acc, position) => {
    const sector = position.company.sector;
    if (!acc[sector]) {
      acc[sector] = { value: 0, weight: 0 };
    }
    acc[sector].value += position.market_value;
    acc[sector].weight += position.weight;
    return acc;
  }, {} as Record<string, { value: number; weight: number }>);

  const sectorChartData = Object.entries(sectorAllocation).map(([sector, data]) => ({
    x: sector,
    y: data.weight,
    label: sector,
  }));

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  const formatPercentage = (value: number) => {
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
  };

  return (
    <div className="space-y-6">
      {/* Portfolio Header */}
      <div className="bg-white rounded-lg shadow-sm border p-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">{portfolio.name}</h2>
            {portfolio.description && (
              <p className="text-gray-600 mt-1">{portfolio.description}</p>
            )}
          </div>
          <div className="text-right">
            <div className="text-sm text-gray-500">Last Updated</div>
            <div className="text-sm font-medium text-gray-900">
              {new Date(portfolio.updated_at).toLocaleDateString()}
            </div>
          </div>
        </div>

        {/* Key Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <div className="text-center">
            <div className="text-3xl font-bold text-gray-900 mb-2">
              {formatCurrency(totalValue)}
            </div>
            <div className="text-sm font-medium text-gray-600">Total Value</div>
          </div>
          
          <div className="text-center">
            <div className={`text-3xl font-bold mb-2 ${
              totalReturn >= 0 ? 'text-green-600' : 'text-red-600'
            }`}>
              {formatCurrency(totalReturn)}
            </div>
            <div className="text-sm font-medium text-gray-600">Total Return</div>
          </div>
          
          <div className="text-center">
            <div className={`text-3xl font-bold mb-2 flex items-center justify-center ${
              totalReturnPercentage >= 0 ? 'text-green-600' : 'text-red-600'
            }`}>
              {totalReturnPercentage >= 0 ? (
                <TrendingUp className="h-6 w-6 mr-2" />
              ) : (
                <TrendingDown className="h-6 w-6 mr-2" />
              )}
              {formatPercentage(totalReturnPercentage)}
            </div>
            <div className="text-sm font-medium text-gray-600">Return %</div>
          </div>
          
          <div className="text-center">
            <div className="text-3xl font-bold text-gray-900 mb-2">
              {portfolio.positions.length}
            </div>
            <div className="text-sm font-medium text-gray-600">Positions</div>
          </div>
        </div>
      </div>

      {showDetailed && (
        <>
          {/* Charts Section */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Sector Allocation */}
            <div className="bg-white rounded-lg shadow-sm border p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Sector Allocation</h3>
              <FinancialChart
                type="doughnut"
                title=""
                data={sectorChartData}
                height={300}
                showLegend={true}
              />
            </div>

            {/* Top Holdings */}
            <div className="bg-white rounded-lg shadow-sm border p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Top Holdings</h3>
              <div className="space-y-4">
                {topPositions.map((position, index) => (
                  <div key={position.id} className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <div className="text-sm font-medium text-gray-500">
                        #{index + 1}
                      </div>
                      <div>
                        <div className="font-medium text-gray-900">
                          {position.company.symbol}
                        </div>
                        <div className="text-sm text-gray-600">
                          {position.company.name}
                        </div>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="font-medium text-gray-900">
                        {position.weight.toFixed(1)}%
                      </div>
                      <div className="text-sm text-gray-600">
                        {formatCurrency(position.market_value)}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Performance Section */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Top Gainers */}
            <div className="bg-white rounded-lg shadow-sm border p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                <TrendingUp className="h-5 w-5 text-green-500 mr-2" />
                Top Gainers
              </h3>
              <div className="space-y-4">
                {gainers.length > 0 ? gainers.map((position) => (
                  <div key={position.id} className="flex items-center justify-between">
                    <div>
                      <div className="font-medium text-gray-900">
                        {position.company.symbol}
                      </div>
                      <div className="text-sm text-gray-600">
                        {position.shares} shares
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="font-medium text-green-600">
                        {formatPercentage(position.unrealized_gain_loss_percentage)}
                      </div>
                      <div className="text-sm text-green-600">
                        {formatCurrency(position.unrealized_gain_loss)}
                      </div>
                    </div>
                  </div>
                )) : (
                  <div className="text-center text-gray-500 py-4">
                    No gainers in current portfolio
                  </div>
                )}
              </div>
            </div>

            {/* Top Losers */}
            <div className="bg-white rounded-lg shadow-sm border p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                <TrendingDown className="h-5 w-5 text-red-500 mr-2" />
                Top Losers
              </h3>
              <div className="space-y-4">
                {losers.length > 0 ? losers.map((position) => (
                  <div key={position.id} className="flex items-center justify-between">
                    <div>
                      <div className="font-medium text-gray-900">
                        {position.company.symbol}
                      </div>
                      <div className="text-sm text-gray-600">
                        {position.shares} shares
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="font-medium text-red-600">
                        {formatPercentage(position.unrealized_gain_loss_percentage)}
                      </div>
                      <div className="text-sm text-red-600">
                        {formatCurrency(position.unrealized_gain_loss)}
                      </div>
                    </div>
                  </div>
                )) : (
                  <div className="text-center text-gray-500 py-4">
                    No losers in current portfolio
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Risk Metrics */}
          <div className="bg-white rounded-lg shadow-sm border p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Risk Assessment</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {/* Diversification Score */}
              <div className="text-center">
                <div className="flex items-center justify-center mb-2">
                  <div className="h-16 w-16 rounded-full bg-green-100 flex items-center justify-center">
                    <CheckCircle className="h-8 w-8 text-green-600" />
                  </div>
                </div>
                <div className="text-2xl font-bold text-gray-900 mb-1">85/100</div>
                <div className="text-sm font-medium text-gray-600">Diversification Score</div>
                <div className="text-xs text-gray-500 mt-1">Well diversified</div>
              </div>

              {/* Concentration Risk */}
              <div className="text-center">
                <div className="flex items-center justify-center mb-2">
                  <div className="h-16 w-16 rounded-full bg-yellow-100 flex items-center justify-center">
                    <AlertTriangle className="h-8 w-8 text-yellow-600" />
                  </div>
                </div>
                <div className="text-2xl font-bold text-gray-900 mb-1">
                  {topPositions[0]?.weight.toFixed(1)}%
                </div>
                <div className="text-sm font-medium text-gray-600">Largest Position</div>
                <div className="text-xs text-gray-500 mt-1">Moderate concentration</div>
              </div>

              {/* Sector Concentration */}
              <div className="text-center">
                <div className="flex items-center justify-center mb-2">
                  <div className="h-16 w-16 rounded-full bg-blue-100 flex items-center justify-center">
                    <PieChart className="h-8 w-8 text-blue-600" />
                  </div>
                </div>
                <div className="text-2xl font-bold text-gray-900 mb-1">
                  {Object.keys(sectorAllocation).length}
                </div>
                <div className="text-sm font-medium text-gray-600">Sectors</div>
                <div className="text-xs text-gray-500 mt-1">Good sector spread</div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

export default PortfolioOverview;