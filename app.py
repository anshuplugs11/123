from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
import json
import re

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

def fetch_instagram_profile(username):
    """Fetch Instagram profile data"""
    url = f"https://www.instagram.com/api/v1/users/web_profile_info/?username={username}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "X-IG-App-ID": "936619743392459",
        "X-ASBD-ID": "198387",
        "X-IG-WWW-Claim": "0",
        "Origin": "https://www.instagram.com",
        "Referer": f"https://www.instagram.com/{username}/",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code == 404:
            return None, "User not found"
        
        if response.status_code != 200:
            return fetch_instagram_profile_fallback(username)
        
        data = response.json()
        
        if 'data' in data and 'user' in data['data']:
            user = data['data']['user']
            
            return {
                "success": True,
                "username": user.get('username', username),
                "full_name": user.get('full_name', 'N/A'),
                "biography": user.get('biography', ''),
                "posts": user.get('edge_owner_to_timeline_media', {}).get('count', 0),
                "followers": user.get('edge_followed_by', {}).get('count', 0),
                "following": user.get('edge_follow', {}).get('count', 0),
                "profile_pic_url": user.get('profile_pic_url_hd', user.get('profile_pic_url', '')),
                "is_private": user.get('is_private', False),
                "is_verified": user.get('is_verified', False),
                "external_url": user.get('external_url', ''),
                "category": user.get('category_name', '')
            }, None
        else:
            return fetch_instagram_profile_fallback(username)
            
    except Exception as e:
        return None, str(e)

def fetch_instagram_profile_fallback(username):
    """Fallback scraping method"""
    url = f"https://www.instagram.com/{username}/"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code != 200:
            return None, f"HTTP Error: {response.status_code}"
        
        # Try to find JSON-LD data
        match = re.search(r'<script type="application/ld\+json">({[^<]+})</script>', response.text)
        
        if match:
            try:
                data = json.loads(match.group(1))
                
                if data.get('@type') == 'Person':
                    return {
                        "success": True,
                        "username": data.get('alternateName', username).replace('@', ''),
                        "full_name": data.get('name', 'N/A'),
                        "biography": data.get('description', ''),
                        "profile_pic_url": data.get('image', ''),
                        "posts": 0,
                        "followers": 0,
                        "following": 0,
                        "is_private": False,
                        "is_verified": False,
                        "external_url": data.get('url', ''),
                        "category": ''
                    }, None
            except:
                pass
        
        return None, "Could not parse profile data"
        
    except Exception as e:
        return None, str(e)

@app.route('/')
def home():
    """API documentation"""
    return jsonify({
        "message": "Instagram Profile API",
        "version": "1.0",
        "endpoints": {
            "/": "API documentation (this page)",
            "/api/ig-profile.php": "Get Instagram profile (query param: username)",
            "/api/health": "Health check endpoint"
        },
        "example": "/api/ig-profile.php?username=instagram",
        "usage": {
            "url": "https://your-domain.vercel.app/api/ig-profile.php?username=USERNAME",
            "method": "GET",
            "params": {
                "username": "Instagram username (required)"
            }
        },
        "note": "This API scrapes public Instagram data and may be rate-limited"
    })

@app.route('/api/health')
def health():
    """Health check endpoint"""
    return jsonify({"status": "ok", "message": "API is running"})

@app.route('/api/ig-profile.php')
def get_profile_php_style():
    """Get Instagram profile (PHP-style endpoint with query parameters)"""
    username = request.args.get('username')
    
    if not username:
        return jsonify({
            "success": False,
            "error": "Username parameter is required",
            "usage": "/api/ig-profile.php?username=USERNAME"
        }), 400
    
    # Clean username
    username = username.strip().replace('@', '')
    
    if len(username) < 1:
        return jsonify({
            "success": False,
            "error": "Invalid username"
        }), 400
    
    profile, error = fetch_instagram_profile(username)
    
    if error:
        return jsonify({
            "success": False,
            "error": error
        }), 404 if error == "User not found" else 500
    
    if profile:
        return jsonify(profile)
    else:
        return jsonify({
            "success": False,
            "error": "Failed to fetch profile"
        }), 500

# Alternative endpoint (REST style) - keep for backward compatibility
@app.route('/api/profile/<username>')
def get_profile_rest_style(username):
    """Get Instagram profile (REST-style endpoint)"""
    if not username or len(username) < 1:
        return jsonify({
            "success": False,
            "error": "Username is required"
        }), 400
    
    # Clean username
    username = username.strip().replace('@', '')
    
    profile, error = fetch_instagram_profile(username)
    
    if error:
        return jsonify({
            "success": False,
            "error": error
        }), 404 if error == "User not found" else 500
    
    if profile:
        return jsonify(profile)
    else:
        return jsonify({
            "success": False,
            "error": "Failed to fetch profile"
        }), 500

@app.errorhandler(404)
def not_found(e):
    return jsonify({
        "success": False,
        "error": "Endpoint not found",
        "available_endpoints": [
            "/",
            "/api/ig-profile.php?username=USERNAME",
            "/api/profile/<username>",
            "/api/health"
        ]
    }), 404

@app.errorhandler(500)
def internal_error(e):
    return jsonify({
        "success": False,
        "error": "Internal server error"
    }), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
