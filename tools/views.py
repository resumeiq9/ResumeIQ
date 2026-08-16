import json
import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.core.mail import EmailMessage
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

logger = logging.getLogger(__name__)

from . import utils
from .forms import ContactForm, SignUpForm


def home(request):
    return render(request, 'tools/home.html')


def tools_page(request):
    return render(request, 'tools/tools.html')


def chatbot(request):
    return render(request, 'tools/chatbot.html')


@require_POST
def chatbot_ask(request):
    """
    Lightweight, rule-based Q&A endpoint for the Chat Bot page. Takes a
    JSON body of {"message": "..."} and returns {"reply": "..."} — no
    external API calls, everything is matched locally in utils.py.
    """
    try:
        data = json.loads(request.body or '{}')
    except ValueError:
        data = {}

    user_message = (data.get('message') or '').strip()
    reply = utils.get_chatbot_reply(user_message)
    return JsonResponse({'reply': reply})


@login_required(login_url='tools:login')
def get_started(request):
    """
    Gate for the hero's "Get Started" CTA. Anonymous visitors are bounced
    to the login page (with ?next= back to here) by @login_required;
    once authenticated they land straight on the tools listing.
    """
    return redirect('tools:tools_page')


def about(request):
    return render(request, 'tools/about.html')


def contact(request):
    form = ContactForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        name = form.cleaned_data['name']
        sender_email = form.cleaned_data['email']
        subject = form.cleaned_data['subject']
        user_message = form.cleaned_data['message']

        body = (
            f"New message from the ResumeIQ contact form.\n\n"
            f"Name: {name}\n"
            f"Email: {sender_email}\n"
            f"Subject: {subject}\n\n"
            f"Message:\n{user_message}"
        )

        try:
            email = EmailMessage(
                subject=f"[ResumeIQ Contact] {subject}",
                body=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[settings.CONTACT_RECIPIENT_EMAIL],
                reply_to=[sender_email],
            )
            email.send(fail_silently=False)
            messages.success(
                request,
                f"Thanks {name}! Your message has been received — we'll get back to you soon."
            )
            form = ContactForm()
        except Exception:
            logger.exception('Failed to send contact form email')
            messages.error(
                request,
                "Sorry, something went wrong sending your message. Please try again in a moment, "
                "or email us directly."
            )

    return render(request, 'tools/contact.html', {'form': form})


def signup_view(request):
    if request.user.is_authenticated:
        return redirect('tools:home')

    form = SignUpForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        user = form.save()
        auth_login(request, user)
        messages.success(request, f'Welcome to ResumeIQ, {user.username}!')
        return redirect('tools:home')

    return render(request, 'tools/signup.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('tools:home')

    form = AuthenticationForm(request, data=request.POST or None)

    if request.method == 'POST' and form.is_valid():
        user = authenticate(
            request,
            username=form.cleaned_data['username'],
            password=form.cleaned_data['password'],
        )
        if user is not None:
            auth_login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')
            next_url = request.POST.get('next') or request.GET.get('next')
            if next_url and url_has_allowed_host_and_scheme(
                next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
            ):
                return redirect(next_url)
            return redirect('tools:home')

    return render(request, 'tools/login.html', {'form': form})


def logout_view(request):
    auth_logout(request)
    messages.info(request, "You've been logged out.")
    return redirect('tools:home')


def resume_creator(request):
    context = {'resume': None, 'submitted': False}

    if request.method == 'POST':
        resume = utils.build_resume_context(request.POST)
        context['resume'] = resume
        context['submitted'] = True

    return render(request, 'tools/resume_creator.html', context)


def resume_analyser(request):
    context = {'result': None, 'error': None}

    if request.method == 'POST' and request.FILES.get('resume_file'):
        uploaded_file = request.FILES['resume_file']
        try:
            text = utils.extract_text_from_upload(uploaded_file)
            if not text.strip():
                context['error'] = (
                    "We couldn't find any readable text in that file. "
                    "If it's a scanned/image-based PDF, try uploading a text-based version."
                )
            else:
                context['result'] = utils.analyse_resume(text)
                context['filename'] = uploaded_file.name
        except (ValueError, ImportError) as exc:
            context['error'] = str(exc)

    return render(request, 'tools/resume_analyser.html', context)


def resume_optimizer(request):
    context = {'result': None, 'error': None}

    if request.method == 'POST':
        target_job_title = request.POST.get('target_job_title', '').strip()
        target_industry = request.POST.get('target_industry', '').strip()
        experience_level = request.POST.get('experience_level', '').strip()
        job_description = request.POST.get('job_description', '').strip()
        uploaded_file = request.FILES.get('resume_file')

        if not uploaded_file:
            context['error'] = 'Please upload your resume.'
        elif not target_job_title:
            context['error'] = "Please enter the job title you're targeting, so ResumeIQ knows what to optimize for."
        else:
            try:
                resume_text = utils.extract_text_from_upload(uploaded_file)
                if not resume_text.strip():
                    context['error'] = (
                        "We couldn't find any readable text in that file. "
                        "If it's a scanned/image-based PDF, try uploading a text-based version."
                    )
                else:
                    context['result'] = utils.optimize_resume_full(
                        resume_text, target_job_title, job_description,
                        target_industry, experience_level,
                    )
                    context['filename'] = uploaded_file.name
            except (ValueError, ImportError) as exc:
                context['error'] = str(exc)

    return render(request, 'tools/resume_optimizer.html', context)
