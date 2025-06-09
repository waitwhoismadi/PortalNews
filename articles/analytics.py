from django.db.models import Sum, Count, Avg, F
from django.utils import timezone
from datetime import timedelta
from .models import Article, Comment, ArticleLike
from collections import defaultdict
import json

class AuthorAnalytics:
    
    def __init__(self, user):
        self.user = user
        self.articles = Article.objects.filter(author=user, status='published')
    
    def get_overview_stats(self):
        return {
            'total_articles': self.articles.count(),
            'total_views': self.articles.aggregate(total=Sum('view_count'))['total'] or 0,
            'total_likes': self.articles.aggregate(total=Sum('like_count'))['total'] or 0,
            'total_comments': self.articles.aggregate(total=Sum('comment_count'))['total'] or 0,
            'average_reading_time': self.articles.aggregate(avg=Avg('reading_time'))['avg'] or 0,
        }
    
    def get_top_articles(self, limit=10):
        return self.articles.annotate(
            engagement_score=F('view_count') + F('like_count') * 2 + F('comment_count') * 3
        ).order_by('-engagement_score')[:limit]
    
    def get_monthly_stats(self, months=6):
        from django.db.models import Count
        from django.db.models.functions import TruncMonth
        
        end_date = timezone.now()
        start_date = end_date - timedelta(days=months * 30)
        
        monthly_data = self.articles.filter(
            created_at__gte=start_date
        ).annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(
            article_count=Count('id'),
            total_views=Sum('view_count'),
            total_likes=Sum('like_count'),
            total_comments=Sum('comment_count')
        ).order_by('month')
        
        return list(monthly_data)
    
    def get_category_performance(self):
        from django.db.models import Count
        
        category_stats = self.articles.values(
            'category__name'
        ).annotate(
            article_count=Count('id'),
            total_views=Sum('view_count'),
            total_likes=Sum('like_count'),
            total_comments=Sum('comment_count'),
            avg_views=Avg('view_count')
        ).order_by('-total_views')
        
        return list(category_stats)
    
    def get_engagement_trends(self, days=30):
        from django.db.models.functions import TruncDate
        
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        recent_articles = self.articles.filter(
            created_at__date__gte=start_date
        ).annotate(
            date=TruncDate('created_at')
        ).values('date').annotate(
            articles_published=Count('id'),
            total_views=Sum('view_count'),
            total_likes=Sum('like_count')
        ).order_by('date')
        
        return list(recent_articles)
    
    def get_reader_insights(self):
        top_commenters = Comment.objects.filter(
            article__author=self.user
        ).values(
            'author__username',
            'author__first_name',
            'author__last_name'
        ).annotate(
            comment_count=Count('id')
        ).order_by('-comment_count')[:10]
        
        most_liked = self.articles.order_by('-like_count')[:5]
        
        return {
            'top_commenters': list(top_commenters),
            'most_liked_articles': most_liked,
        }