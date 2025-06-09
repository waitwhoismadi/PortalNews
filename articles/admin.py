from django.contrib import admin
from .models import Article, Category, ArticleLike, Comment

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'created_at']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name']

@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'category', 'status', 'view_count', 'like_count', 'comment_count', 'created_at']
    list_filter = ['status', 'category', 'created_at']
    search_fields = ['title', 'content']
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ['view_count', 'like_count', 'comment_count', 'word_count', 'reading_time']
    
    fieldsets = (
        ('Content', {
            'fields': ('title', 'slug', 'subtitle', 'content', 'excerpt', 'featured_image')
        }),
        ('Metadata', {
            'fields': ('author', 'category', 'tags', 'status')
        }),
        ('Statistics', {
            'fields': ('view_count', 'like_count', 'comment_count', 'word_count', 'reading_time'),
            'classes': ('collapse',)
        }),
    )

@admin.register(ArticleLike)
class ArticleLikeAdmin(admin.ModelAdmin):
    list_display = ['article', 'user', 'created_at']
    list_filter = ['created_at']

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['article', 'author', 'content_preview', 'parent', 'created_at']
    list_filter = ['created_at', 'article']
    search_fields = ['content', 'author__username']
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content Preview'