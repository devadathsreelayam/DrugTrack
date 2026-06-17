from math import radians, sin, cos, sqrt, asin


def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points
    Returns None if any parameter is None or invalid
    """
    # Check for None values
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return None
    
    try:
        # Convert to float
        lat1 = float(lat1)
        lon1 = float(lon1)
        lat2 = float(lat2)
        lon2 = float(lon2)
        
        # Convert decimal degrees to radians
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        
        # Haversine formula
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        c = 2 * asin(sqrt(a))
        
        # Radius of earth in kilometers
        r = 6371
        return c * r
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def find_nearby_pharmacies(lat, lon, radius_km=10, limit=20):
    """Find pharmacies within a certain radius"""
    from .models import Pharmacy
    
    if lat is None or lon is None:
        return []
    
    pharmacies = Pharmacy.objects.filter(
        status='approved',
        is_active=True,
        latitude__isnull=False,
        longitude__isnull=False
    )
    
    nearby = []
    for pharmacy in pharmacies:
        distance = haversine_distance(lat, lon, pharmacy.latitude, pharmacy.longitude)
        if distance is not None and distance <= radius_km:
            nearby.append({
                'pharmacy': pharmacy,
                'distance': distance
            })
    
    # Sort by distance
    nearby.sort(key=lambda x: x['distance'] if x['distance'] is not None else 999999999)
    return nearby[:limit]


def find_pharmacies_with_drug(lat, lon, drug_name, radius_km=10, limit=20):
    """Find pharmacies with a specific drug in stock"""
    from apps.pharmacy.models import PharmacyStock
    
    # First find nearby pharmacies
    nearby = find_nearby_pharmacies(lat, lon, radius_km, limit * 2)
    
    # Then filter those with the drug in stock
    pharmacies_with_drug = []
    for item in nearby:
        pharmacy = item['pharmacy']
        stock = PharmacyStock.objects.filter(
            pharmacy=pharmacy,
            drug__name__icontains=drug_name,
            available_quantity__gt=0,
            is_available=True
        ).first()
        
        if stock:
            pharmacies_with_drug.append({
                'pharmacy': pharmacy,
                'distance': item['distance'],
                'stock': stock
            })
    
    return pharmacies_with_drug[:limit]
