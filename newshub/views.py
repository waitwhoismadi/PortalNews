from django.shortcuts import render
from django.db.models import Sum
from articles.models import Article, Category

def home_view(request):
    recent_articles = Article.objects.filter(status='published').select_related('author', 'category')[:5]
    
    popular_articles = Article.objects.filter(status='published').order_by('-view_count')[:5]
    
    categories = Category.objects.all()[:8]  
    
    personalized_articles = []
    if request.user.is_authenticated:
        from recommendations.engine import RecommendationEngine
        engine = RecommendationEngine()
        recommendations = engine.get_content_based_recommendations(request.user, limit=5)
        personalized_articles = [rec['article'] for rec in recommendations]
    
    user_stats = None
    if request.user.is_authenticated:
        user_articles = Article.objects.filter(author=request.user)
        user_stats = {
            'articles_count': user_articles.count(),
            'total_views': user_articles.aggregate(total_views=Sum('view_count'))['total_views'] or 0,
            'total_likes': user_articles.aggregate(total_likes=Sum('like_count'))['total_likes'] or 0,
            'reading_time': user_articles.aggregate(total_time=Sum('reading_time'))['total_time'] or 0,
        }
    
    context = {
        'recent_articles': recent_articles,
        'popular_articles': popular_articles,
        'personalized_articles': personalized_articles,
        'categories': categories,
        'user_stats': user_stats,
    }
    
    return render(request, 'home.html', context)