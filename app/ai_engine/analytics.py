"""
AI Engine Analytics Module

Provides strategy clustering, performance analytics, and crowd intelligence.
Enables pattern recognition, trend analysis, and intelligent strategy organization.
"""
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import json
import math
from collections import defaultdict, Counter

from .memory.strategy_store import StrategyStore, StrategyType, TradeOutcome
from .schemas.responses import (
    StrategyCluster, StrategyClusteringResponse, AnalyticsResponse,
    CrowdInsight, CrowdIntelligenceResponse, PerformanceMetrics
)

logger = logging.getLogger(__name__)


class AnalyticsEngine:
    """
    AI Analytics Engine
    
    Responsibilities:
    - Strategy clustering and organization
    - Performance pattern analysis
    - Crowd intelligence aggregation
    - Trend identification and risk assessment
    - Strategy recommendation ranking
    """
    
    def __init__(self, strategy_store: StrategyStore):
        """Initialize analytics engine with strategy store"""
        self.strategy_store = strategy_store
    
    def cluster_strategies(
        self,
        user_id: Optional[str] = None,
        min_strategies: int = 5,
        max_clusters: int = 10
    ) -> StrategyClusteringResponse:
        """
        Cluster strategies based on type, performance, and characteristics
        
        Args:
            user_id: Filter by specific user (None for all users)
            min_strategies: Minimum strategies needed for clustering
            max_clusters: Maximum number of clusters to create
            
        Returns:
            StrategyClusteringResponse with cluster analysis
        """
        try:
            # Get strategies with performance data
            strategies = self._get_strategies_with_performance(user_id)
            
            if len(strategies) < min_strategies:
                return StrategyClusteringResponse(
                    success=False,
                    clusters=[],
                    total_strategies=len(strategies),
                    clustering_method="insufficient_data",
                    performance_summary={
                        "error": f"Need at least {min_strategies} strategies for clustering"
                    }
                )
            
            # Perform clustering
            clusters = self._perform_strategy_clustering(strategies, max_clusters)
            
            # Generate performance summary
            performance_summary = self._generate_clustering_summary(strategies, clusters)
            
            # Generate recommendations
            recommendations = self._generate_clustering_recommendations(clusters)
            
            return StrategyClusteringResponse(
                success=True,
                clusters=clusters,
                total_strategies=len(strategies),
                clustering_method="performance_based",
                performance_summary=performance_summary,
                recommendations=recommendations
            )
            
        except Exception as e:
            logger.error(f"Failed to cluster strategies: {e}")
            return StrategyClusteringResponse(
                success=False,
                clusters=[],
                total_strategies=0,
                clustering_method="error",
                performance_summary={"error": str(e)}
            )
    
    def _get_strategies_with_performance(
        self, 
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get strategies with their performance metrics"""
        try:
            with self.strategy_store.get_connection() as conn:
                base_query = """
                    SELECT s.*, p.total_trades, p.winning_trades, p.losing_trades,
                           p.win_rate, p.average_return, p.performance_score
                    FROM ai_strategies s
                    LEFT JOIN strategy_performance p ON s.strategy_id = p.strategy_id
                    WHERE p.total_trades > 0
                """
                
                params = []
                if user_id:
                    base_query += " AND s.user_id = ?"
                    params.append(user_id)
                
                cursor = conn.execute(base_query, params)
                results = cursor.fetchall()
                columns = [description[0] for description in cursor.description]
                
                strategies = []
                for result in results:
                    strategy_dict = dict(zip(columns, result))
                    
                    # Parse JSON fields
                    try:
                        strategy_dict['tags'] = json.loads(strategy_dict.get('tags', '[]'))
                        strategy_dict['symbols'] = json.loads(strategy_dict.get('symbols', '[]'))
                    except:
                        strategy_dict['tags'] = []
                        strategy_dict['symbols'] = []
                    
                    strategies.append(strategy_dict)
                
                return strategies
                
        except Exception as e:
            logger.error(f"Failed to get strategies with performance: {e}")
            return []
    
    def _perform_strategy_clustering(
        self, 
        strategies: List[Dict[str, Any]], 
        max_clusters: int
    ) -> List[StrategyCluster]:
        """Perform strategy clustering based on multiple criteria"""
        
        # Group by strategy type first
        type_groups = defaultdict(list)
        for strategy in strategies:
            strategy_type = strategy.get('strategy_type', 'unknown')
            type_groups[strategy_type].append(strategy)
        
        clusters = []
        
        for strategy_type, type_strategies in type_groups.items():
            if len(type_strategies) < 2:
                # Single strategy cluster
                strategy = type_strategies[0]
                cluster = self._create_single_strategy_cluster(strategy, strategy_type)
                clusters.append(cluster)
            else:
                # Multiple strategies - cluster by performance and characteristics
                type_clusters = self._cluster_by_performance(type_strategies, strategy_type)
                clusters.extend(type_clusters)
        
        # Sort clusters by performance
        clusters.sort(key=lambda x: x.avg_performance, reverse=True)
        
        # Limit to max_clusters
        return clusters[:max_clusters]
    
    def _create_single_strategy_cluster(
        self, 
        strategy: Dict[str, Any], 
        strategy_type: str
    ) -> StrategyCluster:
        """Create cluster for single strategy"""
        
        return StrategyCluster(
            cluster_id=f"cluster_{strategy['strategy_id'][:8]}",
            cluster_name=f"Single {strategy_type.replace('_', ' ').title()}",
            strategy_type=strategy_type,
            total_strategies=1,
            avg_confidence=strategy.get('confidence_score', 0.0),
            avg_performance=strategy.get('performance_score', 0.0),
            common_tags=strategy.get('tags', []),
            representative_strategy={
                "strategy_id": strategy['strategy_id'],
                "confidence_score": strategy.get('confidence_score', 0.0),
                "win_rate": strategy.get('win_rate', 0.0),
                "total_trades": strategy.get('total_trades', 0)
            }
        )
    
    def _cluster_by_performance(
        self, 
        strategies: List[Dict[str, Any]], 
        strategy_type: str
    ) -> List[StrategyCluster]:
        """Cluster strategies by performance characteristics"""
        
        # Sort by performance score
        strategies.sort(key=lambda x: x.get('performance_score', 0.0), reverse=True)
        
        # Create performance-based clusters
        clusters = []
        
        # High performers (top 30%)
        high_count = max(1, len(strategies) // 3)
        high_performers = strategies[:high_count]
        
        if high_performers:
            clusters.append(self._create_performance_cluster(
                high_performers, strategy_type, "High Performance"
            ))
        
        # Medium performers (middle 40%)
        if len(strategies) > 3:
            medium_start = high_count
            medium_count = max(1, int(len(strategies) * 0.4))
            medium_performers = strategies[medium_start:medium_start + medium_count]
            
            if medium_performers:
                clusters.append(self._create_performance_cluster(
                    medium_performers, strategy_type, "Medium Performance"
                ))
        
        # Low performers (bottom 30%)
        if len(strategies) > 2:
            low_performers = strategies[high_count + (medium_count if len(strategies) > 3 else 0):]
            
            if low_performers:
                clusters.append(self._create_performance_cluster(
                    low_performers, strategy_type, "Developing Performance"
                ))
        
        return clusters
    
    def _create_performance_cluster(
        self, 
        strategies: List[Dict[str, Any]], 
        strategy_type: str, 
        performance_tier: str
    ) -> StrategyCluster:
        """Create cluster from performance-grouped strategies"""
        
        # Calculate averages
        total_strategies = len(strategies)
        avg_confidence = sum(s.get('confidence_score', 0.0) for s in strategies) / total_strategies
        avg_performance = sum(s.get('performance_score', 0.0) for s in strategies) / total_strategies
        
        # Find common tags
        all_tags = []
        for strategy in strategies:
            all_tags.extend(strategy.get('tags', []))
        
        tag_counts = Counter(all_tags)
        common_tags = [tag for tag, count in tag_counts.most_common(5) if count > 1]
        
        # Representative strategy (best performer)
        representative = max(strategies, key=lambda x: x.get('performance_score', 0.0))
        
        return StrategyCluster(
            cluster_id=f"cluster_{strategy_type}_{performance_tier.lower().replace(' ', '_')}",
            cluster_name=f"{performance_tier} {strategy_type.replace('_', ' ').title()}",
            strategy_type=strategy_type,
            total_strategies=total_strategies,
            avg_confidence=avg_confidence,
            avg_performance=avg_performance,
            common_tags=common_tags,
            representative_strategy={
                "strategy_id": representative['strategy_id'],
                "confidence_score": representative.get('confidence_score', 0.0),
                "win_rate": representative.get('win_rate', 0.0),
                "total_trades": representative.get('total_trades', 0),
                "performance_score": representative.get('performance_score', 0.0)
            }
        )
    
    def _generate_clustering_summary(
        self, 
        strategies: List[Dict[str, Any]], 
        clusters: List[StrategyCluster]
    ) -> Dict[str, Any]:
        """Generate summary statistics for clustering results"""
        
        total_strategies = len(strategies)
        total_clusters = len(clusters)
        
        # Overall performance metrics
        overall_performance = sum(s.get('performance_score', 0.0) for s in strategies) / max(1, total_strategies)
        overall_confidence = sum(s.get('confidence_score', 0.0) for s in strategies) / max(1, total_strategies)
        
        # Strategy type distribution
        type_distribution = Counter(s.get('strategy_type', 'unknown') for s in strategies)
        
        # Performance distribution
        high_performers = sum(1 for s in strategies if s.get('performance_score', 0.0) > 0.7)
        medium_performers = sum(1 for s in strategies if 0.3 <= s.get('performance_score', 0.0) <= 0.7)
        low_performers = sum(1 for s in strategies if s.get('performance_score', 0.0) < 0.3)
        
        return {
            "total_strategies": total_strategies,
            "total_clusters": total_clusters,
            "overall_performance": overall_performance,
            "overall_confidence": overall_confidence,
            "strategy_type_distribution": dict(type_distribution),
            "performance_distribution": {
                "high_performers": high_performers,
                "medium_performers": medium_performers,
                "low_performers": low_performers
            },
            "cluster_sizes": [cluster.total_strategies for cluster in clusters],
            "best_cluster": max(clusters, key=lambda x: x.avg_performance).cluster_name if clusters else None
        }
    
    def _generate_clustering_recommendations(
        self, 
        clusters: List[StrategyCluster]
    ) -> List[str]:
        """Generate recommendations based on clustering analysis"""
        
        recommendations = []
        
        if not clusters:
            return ["No clusters available for analysis"]
        
        # Find best performing cluster
        best_cluster = max(clusters, key=lambda x: x.avg_performance)
        recommendations.append(
            f"Focus development on '{best_cluster.cluster_name}' strategies - "
            f"showing {best_cluster.avg_performance:.1%} average performance"
        )
        
        # Find underperforming clusters
        poor_clusters = [c for c in clusters if c.avg_performance < 0.3]
        if poor_clusters:
            recommendations.append(
                f"Review and improve {len(poor_clusters)} underperforming cluster(s) - "
                f"consider revising strategy parameters or risk management"
            )
        
        # Tag-based recommendations
        all_tags = []
        for cluster in clusters:
            all_tags.extend(cluster.common_tags)
        
        popular_tags = Counter(all_tags).most_common(3)
        if popular_tags:
            top_tag = popular_tags[0][0]
            recommendations.append(
                f"'{top_tag}' is the most common strategy characteristic - "
                f"consider developing more strategies with this approach"
            )
        
        # Diversification recommendations
        strategy_types = set(c.strategy_type for c in clusters)
        if len(strategy_types) < 3:
            recommendations.append(
                "Consider diversifying strategy types to reduce correlation risk"
            )
        
        return recommendations
    
    def generate_crowd_intelligence(
        self, 
        days: int = 30,
        min_users: int = 2
    ) -> CrowdIntelligenceResponse:
        """Generate crowd intelligence insights from anonymized data"""
        try:
            # Get crowd insights
            insights = self.strategy_store.get_crowd_insights(limit=20)
            
            # Process insights into structured format
            crowd_insights = []
            for insight_data in insights:
                try:
                    symbols = json.loads(insight_data.get('symbols', '[]'))
                    tags = json.loads(insight_data.get('tags', '[]'))
                except:
                    symbols = []
                    tags = []
                
                crowd_insight = CrowdInsight(
                    insight_id=insight_data['insight_id'],
                    insight_type=insight_data['insight_type'],
                    strategy_type=insight_data.get('strategy_type'),
                    symbols=symbols,
                    tags=tags,
                    user_count=insight_data.get('user_count', 1),
                    total_trades=insight_data.get('total_trades', 0),
                    average_performance=insight_data.get('average_performance', 0.0),
                    confidence_level=insight_data.get('confidence_level', 0.0),
                    risk_score=insight_data.get('risk_score', 0.0)
                )
                crowd_insights.append(crowd_insight)
            
            # Generate trending strategies
            trending_strategies = self._identify_trending_strategies(insights)
            
            # Generate risk alerts
            risk_alerts = self._identify_risk_patterns(insights)
            
            # Popular symbols analysis
            popular_symbols = self._analyze_popular_symbols(insights)
            
            # Performance leaders
            performance_leaders = self._identify_performance_leaders(insights)
            
            return CrowdIntelligenceResponse(
                success=True,
                insights=crowd_insights,
                trending_strategies=trending_strategies,
                risk_alerts=risk_alerts,
                popular_symbols=popular_symbols,
                performance_leaders=performance_leaders,
                generated_at=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Failed to generate crowd intelligence: {e}")
            return CrowdIntelligenceResponse(
                success=False,
                insights=[],
                trending_strategies=[],
                risk_alerts=[],
                popular_symbols=[],
                performance_leaders=[],
                generated_at=datetime.now()
            )
    
    def _identify_trending_strategies(
        self, 
        insights: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Identify trending strategy types and patterns"""
        
        trending = []
        
        # Group by strategy type
        type_performance = defaultdict(list)
        for insight in insights:
            strategy_type = insight.get('strategy_type')
            if strategy_type and insight.get('total_trades', 0) > 5:
                type_performance[strategy_type].append({
                    'performance': insight.get('average_performance', 0.0),
                    'trades': insight.get('total_trades', 0)
                })
        
        # Calculate trending scores
        for strategy_type, performances in type_performance.items():
            if len(performances) >= 2:
                avg_performance = sum(p['performance'] for p in performances) / len(performances)
                total_trades = sum(p['trades'] for p in performances)
                
                # Trending score based on performance and activity
                trending_score = (avg_performance * 0.7) + (min(total_trades / 100.0, 1.0) * 0.3)
                
                if trending_score > 0.3:
                    trending.append({
                        'strategy_type': strategy_type,
                        'trending_score': trending_score,
                        'average_performance': avg_performance,
                        'total_trades': total_trades,
                        'user_count': len(performances)
                    })
        
        # Sort by trending score
        return sorted(trending, key=lambda x: x['trending_score'], reverse=True)[:5]
    
    def _identify_risk_patterns(
        self, 
        insights: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Identify potential risk patterns in crowd behavior"""
        
        risk_alerts = []
        
        # High concentration risk
        symbol_concentration = defaultdict(int)
        for insight in insights:
            try:
                symbols = json.loads(insight.get('symbols', '[]'))
                for symbol in symbols:
                    symbol_concentration[symbol] += insight.get('total_trades', 0)
            except:
                continue
        
        # Alert if any symbol has too much concentration
        total_trades = sum(symbol_concentration.values())
        if total_trades > 0:
            for symbol, trades in symbol_concentration.items():
                concentration = trades / total_trades
                if concentration > 0.3:  # 30% concentration threshold
                    risk_alerts.append({
                        'type': 'concentration_risk',
                        'symbol': symbol,
                        'concentration_percentage': concentration * 100,
                        'message': f"High concentration risk: {symbol} represents {concentration:.1%} of all trades",
                        'severity': 'high' if concentration > 0.5 else 'medium'
                    })
        
        # Poor performance patterns
        poor_performers = [
            insight for insight in insights 
            if insight.get('average_performance', 0.0) < -0.1 and insight.get('total_trades', 0) > 10
        ]
        
        if len(poor_performers) > len(insights) * 0.3:  # More than 30% poor performers
            risk_alerts.append({
                'type': 'widespread_poor_performance',
                'affected_strategies': len(poor_performers),
                'message': f"Widespread poor performance detected in {len(poor_performers)} strategy types",
                'severity': 'high'
            })
        
        return risk_alerts
    
    def _analyze_popular_symbols(
        self, 
        insights: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Analyze most popular trading symbols"""
        
        symbol_stats = defaultdict(lambda: {'trades': 0, 'performance': [], 'strategies': 0})
        
        for insight in insights:
            try:
                symbols = json.loads(insight.get('symbols', '[]'))
                performance = insight.get('average_performance', 0.0)
                trades = insight.get('total_trades', 0)
                
                for symbol in symbols:
                    symbol_stats[symbol]['trades'] += trades
                    symbol_stats[symbol]['performance'].append(performance)
                    symbol_stats[symbol]['strategies'] += 1
            except:
                continue
        
        # Calculate averages and create sorted list
        popular_symbols = []
        for symbol, stats in symbol_stats.items():
            if stats['trades'] > 5:  # Minimum activity threshold
                avg_performance = sum(stats['performance']) / len(stats['performance'])
                popular_symbols.append({
                    'symbol': symbol,
                    'total_trades': stats['trades'],
                    'average_performance': avg_performance,
                    'strategy_count': stats['strategies'],
                    'popularity_score': stats['trades'] * 0.7 + stats['strategies'] * 0.3
                })
        
        # Sort by popularity score
        return sorted(popular_symbols, key=lambda x: x['popularity_score'], reverse=True)[:10]
    
    def _identify_performance_leaders(
        self, 
        insights: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Identify top performing strategy patterns"""
        
        # Filter for high-performing strategies with sufficient data
        leaders = []
        for insight in insights:
            performance = insight.get('average_performance', 0.0)
            trades = insight.get('total_trades', 0)
            
            if performance > 0.2 and trades > 10:  # 20% performance with 10+ trades
                leaders.append({
                    'strategy_type': insight.get('strategy_type', 'unknown'),
                    'performance': performance,
                    'trades': trades,
                    'user_count': insight.get('user_count', 1),
                    'confidence_score': performance * (min(trades / 50.0, 1.0))  # Confidence based on sample size
                })
        
        # Sort by confidence score
        return sorted(leaders, key=lambda x: x['confidence_score'], reverse=True)[:5]
    
    def get_strategy_analytics(
        self,
        strategy_id: str
    ) -> AnalyticsResponse:
        """Get comprehensive analytics for a specific strategy"""
        try:
            # Get strategy performance
            performance = self.strategy_store.get_strategy_performance(strategy_id)
            if not performance:
                return AnalyticsResponse(
                    success=False,
                    analytics_type="strategy_performance",
                    data={"error": "Strategy not found or no performance data"},
                    generated_at=datetime.now()
                )
            
            # Get learning history
            learning_history = self.strategy_store.get_strategy_learning_history(strategy_id)
            
            # Calculate advanced metrics
            analytics_data = {
                "basic_metrics": {
                    "total_trades": performance['total_trades'],
                    "win_rate": performance['win_rate'],
                    "average_return": performance['average_return'],
                    "performance_score": performance['performance_score']
                },
                "learning_insights": len(learning_history),
                "confidence_evolution": self._calculate_confidence_evolution(learning_history),
                "risk_assessment": self._assess_strategy_risk(performance),
                "recommendations": self._generate_strategy_recommendations(performance, learning_history)
            }
            
            return AnalyticsResponse(
                success=True,
                analytics_type="strategy_performance",
                data=analytics_data,
                insights=analytics_data.get("recommendations", []),
                generated_at=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Failed to get strategy analytics: {e}")
            return AnalyticsResponse(
                success=False,
                analytics_type="strategy_performance",
                data={"error": str(e)},
                generated_at=datetime.now()
            )
    
    def _calculate_confidence_evolution(
        self, 
        learning_history: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Calculate how strategy confidence has evolved over time"""
        evolution = []
        
        try:
            for entry in learning_history:
                feedback_content = json.loads(entry.get('feedback_content', '{}'))
                outcome_data = feedback_content.get('outcome_data', {})
                
                evolution.append({
                    'timestamp': entry.get('recorded_at'),
                    'outcome': entry.get('outcome'),
                    'return': entry.get('actual_return'),
                    'confidence_impact': self._calculate_confidence_impact(outcome_data)
                })
        except Exception as e:
            logger.error(f"Failed to calculate confidence evolution: {e}")
        
        return evolution
    
    def _calculate_confidence_impact(self, outcome_data: Dict[str, Any]) -> float:
        """Calculate confidence impact of a trade outcome"""
        outcome = outcome_data.get('outcome', 'neutral')
        actual_return = outcome_data.get('actual_return', 0.0)
        
        if outcome == 'win':
            return min(0.1, actual_return / 10.0)  # Positive impact, capped at 0.1
        elif outcome == 'loss':
            return max(-0.1, actual_return / 10.0)  # Negative impact, capped at -0.1
        else:
            return 0.0
    
    def _assess_strategy_risk(self, performance: Dict[str, Any]) -> Dict[str, Any]:
        """Assess risk characteristics of a strategy"""
        win_rate = performance.get('win_rate', 0.0)
        avg_return = performance.get('average_return', 0.0)
        total_trades = performance.get('total_trades', 0)
        
        # Risk score based on volatility and consistency
        risk_score = 0.0
        
        if win_rate < 0.4:
            risk_score += 0.3  # Low win rate increases risk
        
        if abs(avg_return) > 10.0:
            risk_score += 0.2  # High volatility increases risk
        
        if total_trades < 10:
            risk_score += 0.2  # Insufficient data increases risk
        
        risk_level = "low" if risk_score < 0.3 else "medium" if risk_score < 0.6 else "high"
        
        return {
            "risk_score": risk_score,
            "risk_level": risk_level,
            "factors": {
                "win_rate": win_rate,
                "return_volatility": abs(avg_return),
                "sample_size": total_trades
            }
        }
    
    def _generate_strategy_recommendations(
        self, 
        performance: Dict[str, Any],
        learning_history: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate specific recommendations for strategy improvement"""
        recommendations = []
        
        win_rate = performance.get('win_rate', 0.0)
        avg_return = performance.get('average_return', 0.0)
        total_trades = performance.get('total_trades', 0)
        
        # Performance-based recommendations
        if win_rate < 0.5:
            recommendations.append("Consider tightening entry criteria to improve win rate")
        
        if avg_return < 0:
            recommendations.append("Review risk management - strategy showing negative returns")
        
        if total_trades < 20:
            recommendations.append("Gather more trading data before making significant adjustments")
        
        # Learning-based recommendations
        if len(learning_history) > 5:
            recent_outcomes = [entry.get('outcome') for entry in learning_history[:5]]
            loss_streak = sum(1 for outcome in recent_outcomes if outcome == 'loss')
            
            if loss_streak >= 3:
                recommendations.append("Consider reducing position size - recent loss streak detected")
        
        return recommendations 