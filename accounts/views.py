from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.views import LoginView
from django.core.paginator import Paginator
from django.db.models import Sum
from .forms import CustomUserCreationForm, CustomAuthenticationForm, UserProfileForm
from .models import UserProfile
from articles.models import Article

class CustomLoginView(LoginView):
    form_class = CustomAuthenticationForm
    template_name = 'accounts/login.html'
    
def register_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}! You can now log in.')
            user = authenticate(username=user.username, password=form.cleaned_data['password1'])
            if user:
                login(request, user)
                return redirect('profile_setup')
    else:
        form = CustomUserCreationForm()
    return render(request, 'accounts/register.html', {'form': form})

@login_required
def profile_setup_view(request):
    try:
        profile = request.user.userprofile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=request.user)
    
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('home')
    else:
        form = UserProfileForm(instance=profile)
    
    return render(request, 'accounts/profile_setup.html', {'form': form})

@login_required
def profile_view(request):
    try:
        profile = request.user.userprofile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=request.user)
    
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile')
    else:
        form = UserProfileForm(instance=profile)
    
    return render(request, 'accounts/profile.html', {'form': form, 'profile': profile})

def public_profile_view(request, username):
    user = get_object_or_404(User, username=username)
    try:
        profile = user.userprofile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=user)
    
    articles = Article.objects.filter(author=user, status='published').order_by('-created_at')
    
    paginator = Paginator(articles, 10)
    page_number = request.GET.get('page')
    articles = paginator.get_page(page_number)
    
    user_stats = {
        'articles_count': Article.objects.filter(author=user, status='published').count(),
        'total_views': Article.objects.filter(author=user, status='published').aggregate(
            total_views=Sum('view_count'))['total_views'] or 0,
        'total_likes': Article.objects.filter(author=user, status='published').aggregate(
            total_likes=Sum('like_count'))['total_likes'] or 0,
    }
    
    context = {
        'profile_user': user,
        'profile': profile,
        'articles': articles,
        'user_stats': user_stats,
        'is_own_profile': request.user == user,
    }
    
    return render(request, 'accounts/public_profile.html', context)