from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, F
from django.utils import timezone
from django.http import JsonResponse
from .models import Article, Category, ArticleLike, Comment
from .forms import ArticleForm, CategoryForm, CommentForm
from .analytics import AuthorAnalytics

def article_list(request):
    # Exclude pending and rejected articles from public view
    articles = Article.objects.filter(status='published').select_related('author', 'category')
    
    search_query = request.GET.get('search')
    if search_query:
        articles = articles.filter(
            Q(title__icontains=search_query) |
            Q(content__icontains=search_query) |
            Q(tags__icontains=search_query) |
            Q(author__first_name__icontains=search_query) |
            Q(author__last_name__icontains=search_query)
        )
    
    category_slug = request.GET.get('category')
    selected_category = None
    if category_slug:
        try:
            selected_category = Category.objects.get(slug=category_slug)
            articles = articles.filter(category=selected_category)
        except Category.DoesNotExist:
            pass
    
    paginator = Paginator(articles, 10)  
    page_number = request.GET.get('page')
    articles = paginator.get_page(page_number)
    
    categories = Category.objects.all()
    
    context = {
        'articles': articles,
        'categories': categories,
        'search_query': search_query,
        'selected_category': selected_category,
    }
    return render(request, 'articles/article_list.html', context)

def article_detail(request, slug):
    article = get_object_or_404(Article, slug=slug, status='published')
    
    article.view_count += 1
    article.save(update_fields=['view_count'])
    
    user_has_liked = False
    if request.user.is_authenticated:
        user_has_liked = ArticleLike.objects.filter(article=article, user=request.user).exists()
    
    comments = Comment.objects.filter(article=article, parent=None).select_related('author').order_by('-created_at')
    
    comment_form = CommentForm()
    if request.method == 'POST' and request.user.is_authenticated:
        comment_form = CommentForm(request.POST)
        if comment_form.is_valid():
            comment = comment_form.save(commit=False)
            comment.article = article
            comment.author = request.user
            
            parent_id = request.POST.get('parent_id')
            if parent_id:
                try:
                    parent_comment = Comment.objects.get(id=parent_id, article=article)
                    comment.parent = parent_comment
                except Comment.DoesNotExist:
                    pass
            
            comment.save()
            
            article.comment_count = article.comments.count()
            article.save(update_fields=['comment_count'])
            
            messages.success(request, 'Comment added successfully!')
            return redirect('article_detail', slug=article.slug)
    
    from recommendations.engine import RecommendationEngine
    engine = RecommendationEngine()
    related_articles = engine.get_similar_articles(article, limit=4)
    
    if len(related_articles) < 3:
        category_articles = Article.objects.filter(
            category=article.category,
            status='published'
        ).exclude(id=article.id)[:3]
        
        related_ids = [a.id for a in related_articles]
        for cat_article in category_articles:
            if cat_article.id not in related_ids and len(related_articles) < 4:
                related_articles.append(cat_article)
    
    context = {
        'article': article,
        'user_has_liked': user_has_liked,
        'related_articles': related_articles,
        'comments': comments,
        'comment_form': comment_form,
    }
    return render(request, 'articles/article_detail.html', context)

@login_required
def article_create(request):
    if request.method == 'POST':
        form = ArticleForm(request.POST, request.FILES)
        if form.is_valid():
            article = form.save(commit=False)
            article.author = request.user
            
            # If user is trying to publish, set to pending_approval instead
            if article.status == 'published':
                article.status = 'pending_approval'
                article.save()
                
                # Return JSON response for AJAX popup
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'status': 'pending_approval',
                        'message': 'Your article has been submitted for moderation review. You will be notified once it\'s approved.',
                        'redirect_url': f'/articles/{article.slug}/'
                    })
                
                messages.info(request, 'Your article has been submitted for moderation review.')
                return redirect('my_articles')
            else:
                article.save()
                messages.success(request, f'Article "{article.title}" created successfully!')
                return redirect('article_detail', slug=article.slug)
    else:
        form = ArticleForm()
    
    return render(request, 'articles/article_form.html', {
        'form': form,
        'title': 'Create New Article'
    })

@login_required
def article_edit(request, slug):
    article = get_object_or_404(Article, slug=slug, author=request.user)
    
    if request.method == 'POST':
        form = ArticleForm(request.POST, request.FILES, instance=article)
        if form.is_valid():
            article = form.save(commit=False)
            
            # If user is trying to publish, set to pending_approval instead
            if article.status == 'published' and article.moderated_by is None:
                article.status = 'pending_approval'
                article.save()
                
                # Return JSON response for AJAX popup
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'status': 'pending_approval',
                        'message': 'Your article has been submitted for moderation review. You will be notified once it\'s approved.',
                        'redirect_url': '/articles/my-articles/'
                    })
                
                messages.info(request, 'Your article has been submitted for moderation review.')
                return redirect('my_articles')
            else:
                if article.status == 'published' and not article.published_at:
                    article.published_at = timezone.now()
                article.save()
                messages.success(request, f'Article "{article.title}" updated successfully!')
                return redirect('article_detail', slug=article.slug)
    else:
        form = ArticleForm(instance=article)
    
    return render(request, 'articles/article_form.html', {
        'form': form,
        'article': article,
        'title': 'Edit Article'
    })

@login_required
def my_articles(request):
    articles = Article.objects.filter(author=request.user).order_by('-created_at')
    
    paginator = Paginator(articles, 10)
    page_number = request.GET.get('page')
    articles = paginator.get_page(page_number)
    
    return render(request, 'articles/my_articles.html', {'articles': articles})

@login_required
def toggle_like(request, slug):
    if request.method == 'POST':
        article = get_object_or_404(Article, slug=slug, status='published')
        like, created = ArticleLike.objects.get_or_create(article=article, user=request.user)
        
        if not created:
            like.delete()
            liked = False
        else:
            liked = True
        
        article.like_count = article.likes.count()
        article.save(update_fields=['like_count'])
        
        messages.success(request, 'Article liked!' if liked else 'Article unliked!')
    
    return redirect('article_detail', slug=slug)

def category_list(request):
    categories = Category.objects.all()
    return render(request, 'articles/category_list.html', {'categories': categories})

@login_required
def category_create(request):
    if not request.user.is_staff:
        messages.error(request, 'Permission denied.')
        return redirect('article_list')
    
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Category created successfully!')
            return redirect('category_list')
    else:
        form = CategoryForm()
    
    return render(request, 'articles/category_form.html', {
        'form': form,
        'title': 'Create New Category'
    })

@login_required
def analytics_dashboard(request):
    analytics = AuthorAnalytics(request.user)
    
    context = {
        'overview_stats': analytics.get_overview_stats(),
        'top_articles': analytics.get_top_articles(10),
        'monthly_stats': analytics.get_monthly_stats(6),
        'category_performance': analytics.get_category_performance(),
        'engagement_trends': analytics.get_engagement_trends(30),
        'reader_insights': analytics.get_reader_insights(),
    }
    
    return render(request, 'articles/analytics_dashboard.html', context)

@login_required
def delete_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    
    if request.user == comment.author or request.user == comment.article.author:
        article = comment.article
        comment.delete()
        
        article.comment_count = article.comments.count()
        article.save(update_fields=['comment_count'])
        
        messages.success(request, 'Comment deleted successfully!')
    else:
        messages.error(request, 'Permission denied.')
    
    return redirect('article_detail', slug=comment.article.slug)

# Moderator Views
@user_passes_test(lambda u: u.is_staff)
def moderator_dashboard(request):
    pending_articles = Article.objects.filter(status='pending_approval').select_related('author', 'category').order_by('-created_at')
    rejected_articles = Article.objects.filter(status='rejected').select_related('author', 'moderated_by').order_by('-moderation_date')[:10]
    
    # Statistics
    total_pending = pending_articles.count()
    total_approved_today = Article.objects.filter(
        status='published',
        moderation_date__date=timezone.now().date()
    ).count()
    total_rejected_today = Article.objects.filter(
        status='rejected',
        moderation_date__date=timezone.now().date()
    ).count()
    
    context = {
        'pending_articles': pending_articles,
        'rejected_articles': rejected_articles,
        'total_pending': total_pending,
        'total_approved_today': total_approved_today,
        'total_rejected_today': total_rejected_today,
    }
    return render(request, 'articles/moderator_dashboard.html', context)

@user_passes_test(lambda u: u.is_staff)
def approve_article(request, article_id):
    article = get_object_or_404(Article, id=article_id, status='pending_approval')
    article.status = 'published'
    article.published_at = timezone.now()
    article.moderated_by = request.user
    article.moderation_date = timezone.now()
    article.save()
    
    # Send approval email
    from accounts.email_utils import send_article_approval_email
    try:
        if article.author.email and article.author.userprofile.email_notifications:
            send_article_approval_email(article)
            messages.success(request, f'Article "{article.title}" has been approved and published. Approval email sent to author.')
        else:
            messages.success(request, f'Article "{article.title}" has been approved and published.')
    except Exception as e:
        messages.success(request, f'Article "{article.title}" has been approved and published.')
        messages.warning(request, 'Approval email could not be sent to author.')
    
    return redirect('moderator_dashboard')

@user_passes_test(lambda u: u.is_staff)
def reject_article(request, article_id):
    article = get_object_or_404(Article, id=article_id, status='pending_approval')
    if request.method == 'POST':
        rejection_reason = request.POST.get('rejection_reason', '')
        article.status = 'rejected'
        article.rejection_reason = rejection_reason
        article.moderated_by = request.user
        article.moderation_date = timezone.now()
        article.save()
        
        # Send rejection email
        from accounts.email_utils import send_article_rejection_email
        try:
            if article.author.email and article.author.userprofile.email_notifications:
                send_article_rejection_email(article)
                messages.success(request, f'Article "{article.title}" has been rejected. Feedback email sent to author.')
            else:
                messages.success(request, f'Article "{article.title}" has been rejected.')
        except Exception as e:
            messages.success(request, f'Article "{article.title}" has been rejected.')
            messages.warning(request, 'Rejection email could not be sent to author.')
        
        return redirect('moderator_dashboard')
    return render(request, 'articles/reject_article.html', {'article': article})

@user_passes_test(lambda u: u.is_staff)
def delete_article_admin(request, article_id):
    article = get_object_or_404(Article, id=article_id)
    if request.method == 'POST':
        title = article.title
        article.delete()
        messages.success(request, f'Article "{title}" has been deleted.')
        return redirect('moderator_dashboard')
    return render(request, 'articles/delete_article_confirm.html', {'article': article})