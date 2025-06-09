from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .engine import RecommendationEngine
from .models import ArticleRecommendation
from articles.models import Article

@login_required
def recommendations_view(request):
    engine = RecommendationEngine()
    
    recommendations = engine.get_content_based_recommendations(request.user, limit=20)
    
    trending = engine.get_trending_articles(limit=10)
    
    context = {
        'recommendations': recommendations,
        'trending_articles': trending,
    }
    
    return render(request, 'recommendations/recommendations.html', context)

def get_similar_articles_view(request, article_id):
    try:
        article = Article.objects.get(id=article_id, status='published')
        engine = RecommendationEngine()
        similar_articles = engine.get_similar_articles(article, limit=5)
        
        data = []
        for similar in similar_articles:
            data.append({
                'id': similar.id,
                'title': similar.title,
                'url': similar.get_absolute_url(),
                'author': f"{similar.author.first_name} {similar.author.last_name}",
                'reading_time': similar.reading_time,
                'view_count': similar.view_count,
            })
        
        return JsonResponse({'similar_articles': data})
    
    except Article.DoesNotExist:
        return JsonResponse({'error': 'Article not found'}, status=404)