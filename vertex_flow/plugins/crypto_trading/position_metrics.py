#!/usr/bin/env python3
"""
合约持仓指标计算模块
计算各种持仓相关的风险和收益指标
"""

from typing import Dict, List, Any, Optional
import math


class PositionMetrics:
    """合约持仓指标计算类"""
    
    @staticmethod
    def calculate_position_metrics(position: Dict[str, Any], exchange: str = "okx") -> Dict[str, Any]:
        """
        计算单个持仓的各项指标
        
        Args:
            position: 持仓数据
            exchange: 交易所名称
            
        Returns:
            包含各项指标的字典
        """
        try:
            # 基础数据提取
            symbol = position.get("symbol", "")
            side = position.get("side", "")
            size = float(position.get("size", 0))
            unrealized_pnl = float(position.get("unrealized_pnl", 0))
            
            # 根据交易所获取不同字段
            if exchange.lower() == "okx":
                notional = float(position.get("notional", 0))
                margin = float(position.get("margin", 0))
                entry_price = 0  # OKX API 没有直接提供入场价格
                mark_price = 0   # OKX API 没有直接提供标记价格
                leverage = notional / margin if margin > 0 else 0
            else:  # binance
                notional = float(position.get("notional", 0))
                margin = float(position.get("isolated_margin", 0))
                entry_price = float(position.get("entry_price", 0))
                mark_price = float(position.get("mark_price", 0))
                leverage = float(position.get("leverage", 0))
            
            # 计算各项指标
            metrics = {
                "symbol": symbol,
                "side": side,
                "size": size,
                "notional_value": abs(notional),
                "margin_used": margin,
                "leverage": leverage,
                "unrealized_pnl": unrealized_pnl,
                "entry_price": entry_price,
                "mark_price": mark_price,
            }
            
            # 计算盈亏率
            if margin > 0:
                metrics["pnl_percentage"] = (unrealized_pnl / margin) * 100
            else:
                metrics["pnl_percentage"] = 0
            
            # 计算价格变化率（仅当有入场价格和标记价格时）
            if entry_price > 0 and mark_price > 0:
                price_change = ((mark_price - entry_price) / entry_price) * 100
                if side.lower() == "short":
                    price_change = -price_change
                metrics["price_change_percentage"] = price_change
            else:
                metrics["price_change_percentage"] = 0
            
            # 风险等级评估
            metrics["risk_level"] = PositionMetrics._assess_risk_level(
                leverage, abs(metrics["pnl_percentage"]), abs(notional)
            )
            
            # 持仓价值占比（需要总资产信息，这里先设为0）
            metrics["position_weight"] = 0
            
            return metrics
            
        except Exception as e:
            return {"error": f"Failed to calculate metrics for position: {str(e)}"}
    
    @staticmethod
    def calculate_portfolio_metrics(positions: List[Dict[str, Any]], total_balance: float = 0) -> Dict[str, Any]:
        """
        计算整个投资组合的指标
        
        Args:
            positions: 所有持仓的指标列表
            total_balance: 总资产余额
            
        Returns:
            投资组合指标字典
        """
        try:
            if not positions:
                return {"error": "No positions to calculate"}
            
            # 过滤掉有错误的持仓
            valid_positions = [p for p in positions if "error" not in p]
            
            if not valid_positions:
                return {"error": "No valid positions to calculate"}
            
            # 基础统计
            total_positions = len(valid_positions)
            long_positions = len([p for p in valid_positions if p["side"].lower() == "long"])
            short_positions = len([p for p in valid_positions if p["side"].lower() == "short"])
            
            # 盈亏统计
            total_unrealized_pnl = sum(p["unrealized_pnl"] for p in valid_positions)
            profitable_positions = len([p for p in valid_positions if p["unrealized_pnl"] > 0])
            losing_positions = len([p for p in valid_positions if p["unrealized_pnl"] < 0])
            
            # 保证金和名义价值统计
            total_margin = sum(p["margin_used"] for p in valid_positions)
            total_notional = sum(p["notional_value"] for p in valid_positions)
            
            # 计算平均杠杆
            leverages = [p["leverage"] for p in valid_positions if p["leverage"] > 0]
            avg_leverage = sum(leverages) / len(leverages) if leverages else 0
            
            # 计算胜率
            win_rate = (profitable_positions / total_positions) * 100 if total_positions > 0 else 0
            
            # 计算总盈亏率
            total_pnl_percentage = (total_unrealized_pnl / total_margin) * 100 if total_margin > 0 else 0
            
            # 风险指标
            max_single_loss = min([p["unrealized_pnl"] for p in valid_positions], default=0)
            max_single_gain = max([p["unrealized_pnl"] for p in valid_positions], default=0)
            
            # 持仓集中度（按名义价值）
            if total_notional > 0:
                position_weights = [(p["notional_value"] / total_notional) * 100 for p in valid_positions]
                max_position_weight = max(position_weights, default=0)
                
                # 更新每个持仓的权重
                for i, position in enumerate(valid_positions):
                    position["position_weight"] = position_weights[i]
            else:
                max_position_weight = 0
            
            # 风险等级分布
            risk_distribution = {"low": 0, "medium": 0, "high": 0, "extreme": 0}
            for position in valid_positions:
                risk_level = position.get("risk_level", "medium")
                risk_distribution[risk_level] += 1
            
            portfolio_metrics = {
                "总持仓数量": total_positions,
                "多头持仓": long_positions,
                "空头持仓": short_positions,
                "盈利持仓": profitable_positions,
                "亏损持仓": losing_positions,
                "胜率": f"{win_rate:.2f}%",
                "总未实现盈亏": f"${total_unrealized_pnl:.2f}",
                "总盈亏率": f"{total_pnl_percentage:.2f}%",
                "总保证金": f"${total_margin:.2f}",
                "总名义价值": f"${total_notional:.2f}",
                "平均杠杆": f"{avg_leverage:.2f}x",
                "最大单笔亏损": f"${max_single_loss:.2f}",
                "最大单笔盈利": f"${max_single_gain:.2f}",
                "最大持仓权重": f"{max_position_weight:.2f}%",
                "风险等级分布": risk_distribution,
                "详细持仓": valid_positions
            }
            
            # 如果有总资产信息，计算资产利用率
            if total_balance > 0:
                margin_utilization = (total_margin / total_balance) * 100
                portfolio_metrics["保证金利用率"] = f"{margin_utilization:.2f}%"
                portfolio_metrics["账户总资产"] = f"${total_balance:.2f}"
            
            return portfolio_metrics
            
        except Exception as e:
            return {"error": f"Failed to calculate portfolio metrics: {str(e)}"}
    
    @staticmethod
    def _assess_risk_level(leverage: float, pnl_percentage: float, notional_value: float) -> str:
        """
        评估持仓风险等级
        
        Args:
            leverage: 杠杆倍数
            pnl_percentage: 盈亏百分比（绝对值）
            notional_value: 名义价值
            
        Returns:
            风险等级: low, medium, high, extreme
        """
        risk_score = 0
        
        # 杠杆风险评分
        if leverage >= 20:
            risk_score += 3
        elif leverage >= 10:
            risk_score += 2
        elif leverage >= 5:
            risk_score += 1
        
        # 盈亏风险评分
        if pnl_percentage >= 50:
            risk_score += 3
        elif pnl_percentage >= 20:
            risk_score += 2
        elif pnl_percentage >= 10:
            risk_score += 1
        
        # 持仓规模风险评分
        if notional_value >= 10000:
            risk_score += 2
        elif notional_value >= 5000:
            risk_score += 1
        
        # 风险等级判定
        if risk_score >= 6:
            return "extreme"
        elif risk_score >= 4:
            return "high"
        elif risk_score >= 2:
            return "medium"
        else:
            return "low"
    
    @staticmethod
    def format_metrics_display(metrics: Dict[str, Any]) -> str:
        """
        格式化指标显示
        
        Args:
            metrics: 指标字典
            
        Returns:
            格式化的显示字符串
        """
        if "error" in metrics:
            return f"❌ 计算错误: {metrics['error']}"
        
        # 如果是投资组合指标
        if "总持仓数量" in metrics:
            return PositionMetrics._format_portfolio_display(metrics)
        else:
            return PositionMetrics._format_position_display(metrics)
    
    @staticmethod
    def _format_portfolio_display(metrics: Dict[str, Any]) -> str:
        """格式化投资组合指标显示"""
        display = "\n" + "="*60 + "\n"
        display += "📊 投资组合综合指标\n"
        display += "="*60 + "\n"
        
        # 基础统计
        display += f"📈 持仓概况:\n"
        display += f"  • 总持仓数量: {metrics['总持仓数量']}\n"
        display += f"  • 多头/空头: {metrics['多头持仓']}/{metrics['空头持仓']}\n"
        display += f"  • 盈利/亏损: {metrics['盈利持仓']}/{metrics['亏损持仓']}\n"
        display += f"  • 胜率: {metrics['胜率']}\n\n"
        
        # 盈亏指标
        display += f"💰 盈亏指标:\n"
        display += f"  • 总未实现盈亏: {metrics['总未实现盈亏']}\n"
        display += f"  • 总盈亏率: {metrics['总盈亏率']}\n"
        display += f"  • 最大单笔盈利: {metrics['最大单笔盈利']}\n"
        display += f"  • 最大单笔亏损: {metrics['最大单笔亏损']}\n\n"
        
        # 风险指标
        display += f"⚠️ 风险指标:\n"
        display += f"  • 总保证金: {metrics['总保证金']}\n"
        display += f"  • 总名义价值: {metrics['总名义价值']}\n"
        display += f"  • 平均杠杆: {metrics['平均杠杆']}\n"
        display += f"  • 最大持仓权重: {metrics['最大持仓权重']}\n"
        
        if "保证金利用率" in metrics:
            display += f"  • 保证金利用率: {metrics['保证金利用率']}\n"
            display += f"  • 账户总资产: {metrics['账户总资产']}\n"
        
        # 风险分布
        risk_dist = metrics['风险等级分布']
        display += f"\n🎯 风险等级分布:\n"
        display += f"  • 低风险: {risk_dist['low']} 个\n"
        display += f"  • 中风险: {risk_dist['medium']} 个\n"
        display += f"  • 高风险: {risk_dist['high']} 个\n"
        display += f"  • 极高风险: {risk_dist['extreme']} 个\n"
        
        return display
    
    @staticmethod
    def _format_position_display(metrics: Dict[str, Any]) -> str:
        """格式化单个持仓指标显示"""
        risk_emoji = {
            "low": "🟢",
            "medium": "🟡", 
            "high": "🟠",
            "extreme": "🔴"
        }
        
        risk_level = metrics.get("risk_level", "medium")
        emoji = risk_emoji.get(risk_level, "🟡")
        
        display = f"\n{emoji} {metrics['symbol']} ({metrics['side'].upper()})\n"
        display += f"  • 持仓大小: {metrics['size']:.8f}\n"
        display += f"  • 名义价值: ${metrics['notional_value']:.2f}\n"
        display += f"  • 保证金: ${metrics['margin_used']:.2f}\n"
        display += f"  • 杠杆: {metrics['leverage']:.2f}x\n"
        display += f"  • 未实现盈亏: ${metrics['unrealized_pnl']:.2f}\n"
        display += f"  • 盈亏率: {metrics['pnl_percentage']:.2f}%\n"
        
        if metrics['price_change_percentage'] != 0:
            display += f"  • 价格变化: {metrics['price_change_percentage']:.2f}%\n"
        
        if metrics['position_weight'] > 0:
            display += f"  • 持仓权重: {metrics['position_weight']:.2f}%\n"
        
        display += f"  • 风险等级: {risk_level.upper()}\n"
        
        return display