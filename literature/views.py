from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.core.paginator import Paginator
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.template.loader import get_template
from django.core.mail import send_mail
from xhtml2pdf import pisa
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from io import BytesIO
from openpyxl import Workbook
from django.shortcuts import render, redirect
from django.contrib.auth.views import LoginView
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView
from django.utils import timezone
from django.contrib.auth import logout
from django.db import models 
from .models import Post, Comment, Book, Author, Genre
from .forms import PostForm, CommentForm, BookForm, AuthorProfileForm, GenreForm, UserRegisterForm, UserEditForm
from django.contrib.auth.models import User
import os
from django.conf import settings


def is_author(user):
    return hasattr(user, 'author_profile') and user.author_profile is not None

class PostListView(ListView):
    model = Post
    template_name = 'literature/post/list.html'
    context_object_name = 'posts'
    paginate_by = 5

    def get_queryset(self):
        queryset = super().get_queryset().filter(status='PB')
        
        # Фильтрация по жанру
        genre_slug = self.request.GET.get('genre')
        if genre_slug:
            queryset = queryset.filter(book__genre__name=genre_slug)
        
        # Фильтрация по автору книги
        author_id = self.request.GET.get('author')
        if author_id:
            queryset = queryset.filter(book__author__id=author_id)
        
        # Поиск
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                models.Q(title__icontains=search_query) |
                models.Q(body__icontains=search_query) |
                models.Q(book__title__icontains=search_query)  # Добавлено
            )
        
        return queryset.order_by('-publish')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['genres'] = Genre.objects.all()
        context['authors'] = Author.objects.all()
        return context

class PostDetailView(DetailView):
    model = Post
    template_name = 'literature/post/detail.html'
    context_object_name = 'post'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['comment_form'] = CommentForm()
        return context

class PostCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Post
    form_class = PostForm
    template_name = 'literature/post/create.html'
    success_url = reverse_lazy('literature:post_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.author = self.request.user
        # Добавляем название книги к заголовку поста
        book = form.cleaned_data.get('book')
        if book:
            form.instance.title = f"{book.title} {form.cleaned_data.get('title', '')}"
        
        response = super().form_valid(form)
        
        # Отправка письма о создании поста
        template = settings.EMAIL_TEMPLATES['POST_CREATED']
        send_mail(
            template['subject'],
            template['message'].format(
                username=self.request.user.username,
                post_title=self.object.title
            ),
            settings.DEFAULT_FROM_EMAIL,
            [self.request.user.email],
            fail_silently=False,
        )
        return response
    
    def get_success_url(self):
        return reverse_lazy('literature:post_detail', kwargs={'pk': self.object.pk})

    def test_func(self):
        return is_author(self.request.user)
        

class PostUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Post
    form_class = PostForm
    template_name = 'literature/post/edit.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)

    def test_func(self):
        post = self.get_object()
        return self.request.user == post.author or self.request.user.is_superuser

class PostDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Post
    success_url = reverse_lazy('literature:post_list')
    template_name = 'literature/post/confirm_delete.html'

    def test_func(self):
        post = self.get_object()
        return self.request.user == post.author or self.request.user.is_superuser
    
class BookDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Book
    success_url = reverse_lazy('literature:book_list')
    template_name = 'literature/book/confirm_delete.html'

    def test_func(self):
        book = self.get_object()
        return self.request.user == book.author.user or self.request.user.is_superuser

@login_required
def add_comment(request, pk):
    post = get_object_or_404(Post, pk=pk)
    
    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.post = post
            comment.author = request.user
            comment.save()
            
            # Отправка уведомления автору поста
            if post.author and post.author.email:
                template = settings.EMAIL_TEMPLATES['NEW_COMMENT']
                post_url = request.build_absolute_uri(
                    reverse_lazy('literature:post_detail', kwargs={'pk': post.pk})
                )
                
                send_mail(
                    template['subject'],
                    template['message'].format(
                        username=post.author.username,
                        comment_author=request.user.username,
                        post_title=post.title,
                        comment_text=comment.body[:100],  # Первые 100 символов комментария
                        post_url=post_url
                    ),
                    settings.DEFAULT_FROM_EMAIL,
                    [post.author.email],
                    fail_silently=True,
                )
            
            messages.success(request, 'Ваш комментарий был успешно добавлен.')
            return redirect('literature:post_detail', pk=post.pk)
    else:
        form = CommentForm()
    
    
    return render(request, 'literature/post_detail.html', {
        'post': post,
        'comment_form': form,
        'similar_posts': post.get_similar_posts(),
    })

# Представления для книг
class BookListView(ListView):
    model = Book
    template_name = 'literature/book/list.html'
    context_object_name = 'book_list'
    paginate_by = 10

class BookDetailView(DetailView):
    model = Book
    template_name = 'literature/book/detail.html'

class BookCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Book
    form_class = BookForm
    template_name = 'literature/book/create.html'
    success_url = reverse_lazy('literature:book_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user  # Передаем пользователя в форму
        return kwargs
    
    def form_valid(self, form):
        # Save the form first to create the book instance
        response = super().form_valid(form)
        
        # Отправка письма о создании книги
        template = settings.EMAIL_TEMPLATES['BOOK_CREATED']
        send_mail(
            template['subject'],
            template['message'].format(
                username=self.request.user.username,
                book_title=self.object.title
            ),
            settings.DEFAULT_FROM_EMAIL,
            [self.request.user.email],
            fail_silently=False,
        )
        return response
    
    def test_func(self):
        return is_author(self.request.user) or self.request.user.is_superuser
    
    def get_success_url(self):
        return reverse_lazy('literature:book_detail', kwargs={'pk': self.object.pk})
    
class BookUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Book
    form_class = BookForm
    template_name = 'literature/book/edit.html'
    
    def test_func(self):
        book = self.get_object()
        return self.request.user == book.author.user or self.request.user.is_superuser
    
    def get_success_url(self):
        return reverse_lazy('literature:book_detail', kwargs={'pk': self.object.pk})
    
# Представления для авторов
class AuthorListView(ListView):
    model = Author
    template_name = 'literature/author/list.html'
    context_object_name = 'author_list'
    paginate_by = 10

class AuthorDetailView(DetailView):
    model = Author
    template_name = 'literature/author/detail.html'

@login_required
def become_author(request):
    if request.method == 'POST':
        form = AuthorProfileForm(request.POST, request.FILES)
        if form.is_valid():
            author = form.save(commit=False)
            author.user = request.user
            author.save()
            # Отправка письма о становлении автором
            template = settings.EMAIL_TEMPLATES['BECOME_AUTHOR']
            send_mail(
                template['subject'],
                template['message'].format(username=request.user.username),
                settings.DEFAULT_FROM_EMAIL,
                [request.user.email],
                fail_silently=False,
            )
            messages.success(request, 'Поздравляем! Теперь вы автор.')
            return redirect('literature:dashboard')
    else:
        form = AuthorProfileForm()
    return render(request, 'literature/account/become_author.html', {'form': form})

# Генерация отчетов
@login_required
@user_passes_test(lambda u: u.is_superuser)
def generate_posts_report_pdf(request):
    # Регистрируем шрифт
    font_path = os.path.join(settings.STATICFILES_DIRS[0], 'fonts', 'DejaVuSans.ttf')
    
    try:
        # Регистрируем основной шрифт
        pdfmetrics.registerFont(TTFont('DejaVuSans', font_path))
        
        # Регистрируем bold-версию
        pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', font_path))
        font_name = 'DejaVuSans'
    except Exception as e:
        print(f"Ошибка регистрации шрифта: {e}")
        font_name = 'Helvetica'

    # Создаем PDF-документ
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="posts_report.pdf"'
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=30,
        leftMargin=30,
        topMargin=30,
        bottomMargin=30
    )
    
    # Стили
    styles = getSampleStyleSheet()
    style_heading = styles['Heading1']
    style_heading.fontName = 'DejaVuSans-Bold' if 'DejaVuSans-Bold' in pdfmetrics.getRegisteredFontNames() else 'Helvetica-Bold'
    style_heading.alignment = 1  # Center
    style_heading.fontSize = 16
    
    style_normal = styles['Normal']
    style_normal.fontName = font_name
    style_normal.fontSize = 10
    
    # Собираем содержимое PDF
    elements = []
    
    # Заголовок
    elements.append(Paragraph("Полный отчет о постах", style_heading))
    elements.append(Paragraph(f"Дата генерации: {timezone.now().strftime('%d.%m.%Y %H:%M')}", style_normal))
    elements.append(Spacer(1, 24))
    
    # Данные для таблицы
    data = [['ID', 'Заголовок', 'Автор', 'Книга', 'Статус', 'Дата публикации', 'Комментарии']]
    
    posts = Post.objects.all().order_by('-publish')
    for post in posts:
        data.append([
            str(post.id),
            post.title,
            post.author.username,
            post.book.title,
            post.get_status_display(),
            post.publish.strftime('%d.%m.%Y %H:%M'),
            str(post.comments.count())
        ])
    
    # Создаем таблицу
    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#6d2e46')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#d82e70')),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'DejaVuSans-Bold' if 'DejaVuSans-Bold' in pdfmetrics.getRegisteredFontNames() else 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f5f1e8')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTNAME', (0, 1), (-1, -1), font_name),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    
    elements.append(table)
    
    # Собираем PDF
    doc.build(elements)
    
    # Получаем содержимое буфера
    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)
    
    return response

@login_required
@user_passes_test(lambda u: u.is_superuser)
def generate_posts_report_excel(request):
    posts = Post.objects.all().order_by('-publish')
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Отчет о постах"
    
    ws.append(['ID', 'Заголовок', 'Автор', 'Книга', 'Статус', 'Дата публикации', 'Комментарии'])
    

    for post in posts:
        comment_count = post.comments.count()
        
        ws.append([
            post.id,
            post.title,
            post.author.username,
            post.book.title,
            post.get_status_display(),
            post.publish.strftime('%Y-%m-%d %H:%M'),
            comment_count
        ])
    
    # Сохраняем в response
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=posts_report.xlsx'
    wb.save(response)
    
    return response

# Dashboard views
@login_required
def dashboard(request):
    context = {}
    if is_author(request.user):
        context['author_posts'] = Post.objects.filter(author=request.user).order_by('-publish')[:5]
        context['author_books'] = Book.objects.filter(author=request.user.author_profile)[:5]
    return render(request, 'literature/account/dashboard.html', context)

@login_required
def profile_edit(request):
    if request.method == 'POST':
        user_form = UserEditForm(request.POST, instance=request.user)
        
        if is_author(request.user):
            author_form = AuthorProfileForm(request.POST, request.FILES, instance=request.user.author_profile)
        else:
            author_form = None
        
        if user_form.is_valid() and (author_form is None or author_form.is_valid()):
            user_form.save()
            if author_form:
                author_form.save()
            messages.success(request, 'Ваш профиль был успешно обновлен.')
            return redirect('literature:profile_edit')
    else:
        user_form = UserEditForm(instance=request.user)
        if is_author(request.user):
            author_form = AuthorProfileForm(instance=request.user.author_profile)
        else:
            author_form = None
    
    return render(request, 'literature/account/edit.html', {
        'user_form': user_form,
        'author_form': author_form
    })

def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Отправка приветственного письма
            template = settings.EMAIL_TEMPLATES['WELCOME']
            send_mail(
                template['subject'],
                template['message'].format(username=user.username),
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )
            return redirect(reverse_lazy('login'))
    else:
        form = UserRegisterForm()
    return render(request, 'literature/account/register.html', {'form': form})

def custom_logout(request):
    logout(request)
    return redirect('literature:post_list')

@login_required
def delete_comment(request, pk):
    comment = get_object_or_404(Comment, pk=pk)
    
    # Проверяем, что пользователь - автор комментария или суперпользователь
    if request.user == comment.author or request.user.is_superuser:
        post_pk = comment.post.pk
        comment.delete()
        messages.success(request, 'Комментарий успешно удален.')
        return redirect('literature:post_detail', pk=post_pk)
    else:
        messages.error(request, 'У вас нет прав для удаления этого комментария.')
        return redirect('literature:post_detail', pk=comment.post.pk)