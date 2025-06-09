from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.contrib.auth.models import User
import logging

logger = logging.getLogger(__name__)

def send_welcome_email(user):
    """Send welcome email to new user"""
    try:
        subject = f'Welcome to {settings.SITE_NAME}!'
        
        # Render HTML template
        html_content = render_to_string('emails/welcome_email.html', {
            'user': user,
            'site_name': settings.SITE_NAME,
            'site_url': settings.SITE_URL,
        })
        
        # Create plain text version
        text_content = strip_tags(html_content)
        
        # Create email message
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email]
        )
        email.attach_alternative(html_content, "text/html")
        
        # Send email
        email.send()
        logger.info(f'Welcome email sent to {user.email}')
        return True
        
    except Exception as e:
        logger.error(f'Failed to send welcome email to {user.email}: {str(e)}')
        return False

def send_article_approval_email(article):
    """Send email when article is approved"""
    try:
        subject = f'Your article "{article.title}" has been approved!'
        
        html_content = render_to_string('emails/article_approved.html', {
            'article': article,
            'author': article.author,
            'site_name': settings.SITE_NAME,
            'site_url': settings.SITE_URL,
            'article_url': f"{settings.SITE_URL}{article.get_absolute_url()}",
        })
        
        text_content = strip_tags(html_content)
        
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[article.author.email]
        )
        email.attach_alternative(html_content, "text/html")
        email.send()
        
        logger.info(f'Approval email sent to {article.author.email} for article "{article.title}"')
        return True
        
    except Exception as e:
        logger.error(f'Failed to send approval email for article "{article.title}": {str(e)}')
        return False

def send_article_rejection_email(article):
    """Send email when article is rejected"""
    try:
        subject = f'Your article "{article.title}" needs revision'
        
        html_content = render_to_string('emails/article_rejected.html', {
            'article': article,
            'author': article.author,
            'site_name': settings.SITE_NAME,
            'site_url': settings.SITE_URL,
            'moderator': article.moderated_by,
            'rejection_reason': article.rejection_reason,
        })
        
        text_content = strip_tags(html_content)
        
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[article.author.email]
        )
        email.attach_alternative(html_content, "text/html")
        email.send()
        
        logger.info(f'Rejection email sent to {article.author.email} for article "{article.title}"')
        return True
        
    except Exception as e:
        logger.error(f'Failed to send rejection email for article "{article.title}": {str(e)}')
        return False

def send_password_reset_notification(user, reset_url):
    """Send notification that password was reset"""
    try:
        subject = 'Your password has been reset'
        
        html_content = render_to_string('emails/password_reset_notification.html', {
            'user': user,
            'site_name': settings.SITE_NAME,
            'site_url': settings.SITE_URL,
            'reset_url': reset_url,
        })
        
        text_content = strip_tags(html_content)
        
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email]
        )
        email.attach_alternative(html_content, "text/html")
        email.send()
        
        logger.info(f'Password reset notification sent to {user.email}')
        return True
        
    except Exception as e:
        logger.error(f'Failed to send password reset notification to {user.email}: {str(e)}')
        return False