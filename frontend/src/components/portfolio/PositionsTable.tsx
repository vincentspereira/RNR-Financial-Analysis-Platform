/**
 * Portfolio Positions Table Component
 */
import React, { useState, useMemo } from 'react';
import {
  ChevronUp,
  ChevronDown,
  TrendingUp,
  TrendingDown,
  MoreHorizontal,
  Edit,
  Trash2,
  BarChart3,
  ExternalLink,
} from 'lucide-react';
import { PortfolioPosition } from '@/types/financial';

interface PositionsTableProps {
  positions: PortfolioPosition[];
  onEditPosition?: (position: PortfolioPosition) => void;
  onDeletePosition?: (positionId: string) => void;
  onAnalyzeCompany?: (companyId: string) => void;
}

type SortField = 'symbol' | 'weight' | 'market_value' | 'unrealized_gain_loss_percentage' | 'purchase_date';
type SortDirection = 'asc' | 'desc';

export function PositionsTable({
  positions,
  onEditPosition,
  onDeletePosition,
  onAnalyzeCompany,
}: PositionsTableProps) {
  const [sortField, setSortField] = useState<SortField>('weight');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');
  const [activeDropdown, setActiveDropdown] = useState<string | null>(null);

  const sortedPositions = useMemo(() => {
    return [...positions].sort((a, b) => {
      let aValue: any;
      let bValue: any;

      switch (sortField) {
        case 'symbol':
          aValue = a.company.symbol;
          bValue = b.company.symbol;
          break;
        case 'weight':
          aValue = a.weight;
          bValue = b.weight;
          break;
        case 'market_value':
          aValue = a.market_value;
          bValue = b.market_value;
          break;
        case 'unrealized_gain_loss_percentage':
          aValue = a.unrealized_gain_loss_percentage;
          bValue = b.unrealized_gain_loss_percentage;
          break;
        case 'purchase_date':
          aValue = new Date(a.purchase_date);
          bValue = new Date(b.purchase_date);
          break;
        default:
          return 0;
      }

      if (aValue < bValue) return sortDirection === 'asc' ? -1 : 1;
      if (aValue > bValue) return sortDirection === 'asc' ? 1 : -1;
      return 0;
    });
  }, [positions, sortField, sortDirection]);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

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

  const SortButton = ({ field, children }: { field: SortField; children: React.ReactNode }) => (
    <button
      onClick={() => handleSort(field)}
      className="flex items-center space-x-1 text-left font-medium text-gray-900 hover:text-gray-700"
    >
      <span>{children}</span>
      {sortField === field && (
        sortDirection === 'asc' ? (
          <ChevronUp className="h-4 w-4" />
        ) : (
          <ChevronDown className="h-4 w-4" />
        )
      )}
    </button>
  );

  const ActionDropdown = ({ position }: { position: PortfolioPosition }) => (
    <div className="relative">
      <button
        onClick={() => setActiveDropdown(activeDropdown === position.id ? null : position.id)}
        className="p-1 rounded-md hover:bg-gray-100"
      >
        <MoreHorizontal className="h-4 w-4 text-gray-400" />
      </button>
      
      {activeDropdown === position.id && (
        <div className="absolute right-0 mt-2 w-48 bg-white rounded-md shadow-lg border z-10">
          <div className="py-1">
            {onAnalyzeCompany && (
              <button
                onClick={() => {
                  onAnalyzeCompany(position.company.id);
                  setActiveDropdown(null);
                }}
                className="flex items-center px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 w-full text-left"
              >
                <BarChart3 className="h-4 w-4 mr-2" />
                Analyze Company
              </button>
            )}
            {onEditPosition && (
              <button
                onClick={() => {
                  onEditPosition(position);
                  setActiveDropdown(null);
                }}
                className="flex items-center px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 w-full text-left"
              >
                <Edit className="h-4 w-4 mr-2" />
                Edit Position
              </button>
            )}
            <button
              className="flex items-center px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 w-full text-left"
            >
              <ExternalLink className="h-4 w-4 mr-2" />
              View Details
            </button>
            {onDeletePosition && (
              <button
                onClick={() => {
                  onDeletePosition(position.id);
                  setActiveDropdown(null);
                }}
                className="flex items-center px-4 py-2 text-sm text-red-600 hover:bg-red-50 w-full text-left"
              >
                <Trash2 className="h-4 w-4 mr-2" />
                Remove Position
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );

  return (
    <div className="bg-white rounded-lg shadow-sm border overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-200">
        <h3 className="text-lg font-semibold text-gray-900">Portfolio Positions</h3>
        <p className="text-sm text-gray-600 mt-1">
          {positions.length} positions • Total value: {formatCurrency(positions.reduce((sum, p) => sum + p.market_value, 0))}
        </p>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                <SortButton field="symbol">Company</SortButton>
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Shares
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Avg Cost
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Current Price
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                <SortButton field="market_value">Market Value</SortButton>
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                <SortButton field="weight">Weight</SortButton>
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                <SortButton field="unrealized_gain_loss_percentage">Gain/Loss</SortButton>
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                <SortButton field="purchase_date">Purchase Date</SortButton>
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {sortedPositions.map((position) => (
              <tr key={position.id} className="hover:bg-gray-50">
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="flex items-center">
                    <div className="flex-shrink-0 h-10 w-10">
                      <div className="h-10 w-10 rounded-full bg-gray-200 flex items-center justify-center">
                        <span className="text-sm font-medium text-gray-700">
                          {position.company.symbol.charAt(0)}
                        </span>
                      </div>
                    </div>
                    <div className="ml-4">
                      <div className="text-sm font-medium text-gray-900">
                        {position.company.symbol}
                      </div>
                      <div className="text-sm text-gray-500">
                        {position.company.name}
                      </div>
                    </div>
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {position.shares.toLocaleString()}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {formatCurrency(position.average_cost)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {formatCurrency(position.current_price)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                  {formatCurrency(position.market_value)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {position.weight.toFixed(1)}%
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm">
                  <div className="flex items-center">
                    {position.unrealized_gain_loss_percentage >= 0 ? (
                      <TrendingUp className="h-4 w-4 text-green-500 mr-1" />
                    ) : (
                      <TrendingDown className="h-4 w-4 text-red-500 mr-1" />
                    )}
                    <div className={`${
                      position.unrealized_gain_loss_percentage >= 0 ? 'text-green-600' : 'text-red-600'
                    }`}>
                      <div className="font-medium">
                        {formatPercentage(position.unrealized_gain_loss_percentage)}
                      </div>
                      <div className="text-xs">
                        {formatCurrency(position.unrealized_gain_loss)}
                      </div>
                    </div>
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {new Date(position.purchase_date).toLocaleDateString()}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  <ActionDropdown position={position} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {positions.length === 0 && (
        <div className="text-center py-12">
          <div className="text-gray-400 mb-4">
            <BarChart3 className="h-12 w-12 mx-auto" />
          </div>
          <h3 className="text-lg font-medium text-gray-900 mb-2">No positions yet</h3>
          <p className="text-gray-600">Add your first position to start tracking your portfolio.</p>
        </div>
      )}
    </div>
  );
}

export default PositionsTable;