from django.shortcuts import render

# Create your views here.
def symptom_checker(request):
    return render(request, 'symptom_checker/symptom_checker.html', {})