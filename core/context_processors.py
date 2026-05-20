from .models import Medicine

def site_context(request):
    return {
        'site_name': 'DrugTrack',
        'current_year': 2026,
        'medicines_list': Medicine.objects.all()[:10]  # For dropdowns
    }