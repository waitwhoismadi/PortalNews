from django.contrib.auth.views import PasswordResetView, PasswordResetConfirmView
from django.contrib.auth.forms import PasswordResetForm
from django.urls import reverse_lazy
from django.contrib import messages
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.contrib.auth import get_user_model
from .email_utils import send_password_reset_notification

User = get_user_model()

class CustomPasswordResetForm(PasswordResetForm):
    def send_mail(self, subject_template_name, email_template_name,
                  context, from_email, to_email, html_email_template_name=None):
        try:
            html_content = render_to_string('emails/password_reset_request.html', context)
            text_content = strip_tags(html_content)
            
            email = EmailMultiAlternatives(
                subject=f'🔐 {settings.SITE_NAME} - Password Reset Request',
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[to_email]
            )
            email.attach_alternative(html_content, "text/html")
            email.send()
            
        except Exception as e:
            super().send_mail(subject_template_name, email_template_name,
                            context, from_email, to_email, html_email_template_name)

class CustomPasswordResetView(PasswordResetView):
    template_name = 'accounts/password_reset.html'
    success_url = reverse_lazy('password_reset_done')
    form_class = CustomPasswordResetForm
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request, 
            'Password reset instructions have been sent to your email address.'
        )
        return response

class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'accounts/password_reset_confirm.html'
    success_url = reverse_lazy('password_reset_complete')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        
        user = form.user
        try:
            if user.email:
                reset_url = f"{settings.SITE_URL}/accounts/login/"
                send_password_reset_notification(user, reset_url)
                messages.success(
                    self.request, 
                    'Your password has been reset successfully! A confirmation email has been sent.'
                )
            else:
                messages.success(
                    self.request, 
                    'Your password has been reset successfully!'
                )
        except Exception as e:
            messages.success(
                self.request, 
                'Your password has been reset successfully!'
            )
            messages.warning(
                self.request,
                'Confirmation email could not be sent, but your password is updated.'
            )
        
        return response