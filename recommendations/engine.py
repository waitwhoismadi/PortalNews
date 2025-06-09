import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from django.db import models
from django.contrib.auth.models import User
from django.db.models import Q, Count, Avg, F
from articles.models import Article, ArticleLike
from .models import UserReadingHistory, UserPreferences, ArticleRecommendation
import re
from collections import defaultdict, Counter

class RecommendationEngine:
    
    def __init__(self):
        self.vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words='english',
            ngram_range=(1, 2)
        )
    
    def get_article_content_for_analysis(self, article):

        content = f"{article.title} {article.content}"
        if article.tags:
            content += f" {article.tags.replace(',', ' ')}"
        
        content = re.sub(r'<[^>]+>', '', content)
        content = re.sub(r'[^\w\s]', ' ', content)
        content = re.sub(r'\s+', ' ', content).strip().lower()
        
        return content
    
    def update_user_preferences(self, user):
        try:
            preferences, created = UserPreferences.objects.get_or_create(user=user)
        except:
            return
        
        liked_articles = Article.objects.filter(likes__user=user, status='published')
        
        read_articles = Article.objects.filter(
            Q(likes__user=user) |  
            Q(author=user)  
        ).distinct()
        
        if not read_articles.exists():
            return
        
        category_scores = defaultdict(float)
        tag_scores = defaultdict(float)
        
        for article in read_articles:
            weight = 1.0
            if liked_articles.filter(id=article.id).exists():
                weight = 2.0
            
            if article.category:
                category_scores[article.category.name] += weight
            
            if article.tags:
                tags = [tag.strip().lower() for tag in article.tags.split(',')]
                for tag in tags:
                    if tag:
                        tag_scores[tag] += weight
        
        if category_scores:
            max_cat_score = max(category_scores.values())
            category_scores = {k: v/max_cat_score for k, v in category_scores.items()}
        
        if tag_scores:
            max_tag_score = max(tag_scores.values())
            tag_scores = {k: v/max_tag_score for k, v in tag_scores.items()}
        
        preferences.category_scores = dict(category_scores)
        preferences.tag_scores = dict(tag_scores)
        preferences.save()
    
    def get_content_based_recommendations(self, user, limit=10):
        self.update_user_preferences(user)
        
        try:
            preferences = UserPreferences.objects.get(user=user)
        except UserPreferences.DoesNotExist:
            return []
        
        user_article_ids = set()
        user_article_ids.update(
            ArticleLike.objects.filter(user=user).values_list('article_id', flat=True)
        )
        user_article_ids.update(
            Article.objects.filter(author=user).values_list('id', flat=True)
        )
        
        candidate_articles = Article.objects.filter(
            status='published'
        ).exclude(id__in=user_article_ids)
        
        if not candidate_articles.exists():
            return []
        
        recommendations = []
        
        for article in candidate_articles:
            score = 0.0
            
            if article.category and article.category.name in preferences.category_scores:
                score += preferences.category_scores[article.category.name] * 0.6
            
            if article.tags:
                article_tags = [tag.strip().lower() for tag in article.tags.split(',')]
                tag_score = 0
                tag_count = 0
                for tag in article_tags:
                    if tag in preferences.tag_scores:
                        tag_score += preferences.tag_scores[tag]
                        tag_count += 1
                if tag_count > 0:
                    score += (tag_score / tag_count) * 0.4
            
            popularity_score = min(article.view_count / 100, 1.0) * 0.1
            score += popularity_score
            
            import datetime
            days_old = (datetime.datetime.now().date() - article.created_at.date()).days
            recency_score = max(0, (30 - days_old) / 30) * 0.1
            score += recency_score
            
            if score > 0.1:  
                recommendations.append({
                    'article': article,
                    'score': score,
                    'algorithm': 'content_based'
                })
        
        recommendations.sort(key=lambda x: x['score'], reverse=True)
        return recommendations[:limit]
    
    def get_similar_articles(self, article, limit=5):
        if not article:
            return []
        
        all_articles = Article.objects.filter(
            status='published'
        ).exclude(id=article.id)
        
        if not all_articles.exists():
            return []
        
        recommendations = []
        
        for other_article in all_articles:
            score = 0.0
            
            if article.category and other_article.category:
                if article.category == other_article.category:
                    score += 0.7
            
            if article.tags and other_article.tags:
                article_tags = set(tag.strip().lower() for tag in article.tags.split(','))
                other_tags = set(tag.strip().lower() for tag in other_article.tags.split(','))
                
                if article_tags and other_tags:
                    intersection = len(article_tags.intersection(other_tags))
                    union = len(article_tags.union(other_tags))
                    if union > 0:
                        score += (intersection / union) * 0.5
            
            if article.author == other_article.author:
                score += 0.2
            
            popularity_score = min(other_article.view_count / 100, 1.0) * 0.1
            score += popularity_score
            
            if score > 0.1:
                recommendations.append({
                    'article': other_article,
                    'score': score
                })
        
        recommendations.sort(key=lambda x: x['score'], reverse=True)
        return [rec['article'] for rec in recommendations[:limit]]
    
    def get_trending_articles(self, limit=10):
        from django.utils import timezone
        from datetime import timedelta
        
        last_week = timezone.now() - timedelta(days=7)
        
        trending = Article.objects.filter(
            status='published',
            created_at__gte=last_week
        ).annotate(
            engagement_score=F('view_count') + F('like_count') * 2
        ).order_by('-engagement_score')
        
        return trending[:limit]