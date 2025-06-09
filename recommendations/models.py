from django.db import models
from django.contrib.auth.models import User
from articles.models import Article

class UserReadingHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    article = models.ForeignKey(Article, on_delete=models.CASCADE)
    read_at = models.DateTimeField(auto_now_add=True)
    reading_time_seconds = models.PositiveIntegerField(default=0)
    completed = models.BooleanField(default=False)  
    
    class Meta:
        unique_together = ('user', 'article')
        ordering = ['-read_at']
    
    def __str__(self):
        return f"{self.user.username} read {self.article.title}"

class UserPreferences(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    category_scores = models.JSONField(default=dict)  
    tag_scores = models.JSONField(default=dict)  
    author_scores = models.JSONField(default=dict) 
    last_updated = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username}'s preferences"

class ArticleRecommendation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    article = models.ForeignKey(Article, on_delete=models.CASCADE)
    score = models.FloatField() 
    algorithm = models.CharField(max_length=50)  
    created_at = models.DateTimeField(auto_now_add=True)
    clicked = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ('user', 'article')
        ordering = ['-score', '-created_at']
    
    def __str__(self):
        return f"Recommend {self.article.title} to {self.user.username} (score: {self.score:.2f})"