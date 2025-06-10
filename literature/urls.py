from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

app_name = 'literature'

urlpatterns = [
    # Посты
    path('', views.PostListView.as_view(), name='post_list'),
    #path('post/<int:pk>/<slug:slug>/', views.PostDetailView.as_view(), name='post_detail'),
    path('posts/<int:pk>/', views.PostDetailView.as_view(), name='post_detail'),
    path('post/new/', views.PostCreateView.as_view(), name='post_create'),
    path('posts/<int:pk>/edit/', views.PostUpdateView.as_view(), name='post_edit'),
    path('posts/<int:pk>/delete/', views.PostDeleteView.as_view(), name='post_delete'),
    path('posts/<int:pk>/comment/', views.add_comment, name='add_comment'),
    
    # Книги
    path('books/', views.BookListView.as_view(), name='book_list'),
    path('books/<int:pk>/', views.BookDetailView.as_view(), name='book_detail'),
    path('books/new/', views.BookCreateView.as_view(), name='book_create'),
    path('books/<int:pk>/edit/', views.BookUpdateView.as_view(), name='book_edit'),
    path('books/<int:pk>/delete/', views.BookDeleteView.as_view(), name='book_delete'),
    
    # Авторы
    path('authors/', views.AuthorListView.as_view(), name='author_list'),
    path('authors/<int:pk>/', views.AuthorDetailView.as_view(), name='author_detail'),
    path('become-author/', views.become_author, name='become_author'),
    
    # Отчеты
    path('reports/posts/pdf/', views.generate_posts_report_pdf, name='posts_report_pdf'),
    path('reports/posts/excel/', views.generate_posts_report_excel, name='posts_report_excel'),
    
    # Профиль
    path('dashboard/', views.dashboard, name='dashboard'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),

    # Регистрация пользователя
    path('register/', views.register, name='register'),

    # Выход из аккаунта
    path('accounts/logout/', views.custom_logout, name='logout'),

    path('comments/<int:pk>/delete/', views.delete_comment, name='delete_comment'),
    
]