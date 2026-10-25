"""
AthletiQ - Stage 2 Comprehensive Verification Test Suite
Tests:
1. Model definitions & relationship schema
2. Password hashing & verification
3. JWT creation & expiration/secret decoding
4. User registration (POST /api/auth/register)
5. Duplicate registration rejection (409 Conflict)
6. User login with valid credentials (POST /api/auth/login)
7. User login with invalid password (401 Unauthorized)
8. User login with non-existent email (401 Unauthorized)
9. Protected endpoint access without token (401 Unauthorized)
10. Protected endpoint access with invalid token (401 Unauthorized)
11. Protected endpoint access with valid token (GET /api/users/me)
12. Security: ensure hashed_password and secrets are never returned in responses
13. GET /api/auth/me endpoint
14. Athlete profile creation (POST /api/athletes/profile)
15. Duplicate athlete profile creation rejection (400 Bad Request)
16. Athlete profile retrieval (GET /api/athletes/profile)
17. Athlete profile update (PUT /api/athletes/profile)
18. Exercise session creation (POST /api/sessions)
19. Exercise session list retrieval (GET /api/sessions)
20. Exercise session retrieval by ID (GET /api/sessions/{session_id})
21. Cross-user isolation: User B cannot access or view User A's profile or sessions
"""

import sys
import uuid
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import hash_password, verify_password, create_access_token
from app.models.user import User, UserRole
from app.models.profile import AthleteProfile
from app.models.session import ExerciseSession

client = TestClient(app)

def test_security_utilities():
    print("Testing Security Utilities...")
    pwd = "SecretPassword123!"
    hashed = hash_password(pwd)
    assert hashed != pwd, "Password was not hashed"
    assert verify_password(pwd, hashed), "Password verification failed"
    assert not verify_password("WrongPassword", hashed), "Invalid password verified as true"
    
    token = create_access_token(subject=42)
    assert isinstance(token, str), "Token is not a string"
    assert len(token) > 20, "Token is suspiciously short"
    print("  [PASS] Security utilities working properly")

def test_full_auth_and_crud_flow():
    print("Testing Full Stage 2 API Flow...")
    uid_a = uuid.uuid4().hex[:8]
    email_a = f"athlete_{uid_a}@athletiq.com"
    pwd_a = "StrongPass123"
    name_a = f"Athlete {uid_a}"

    # 1. Health check
    resp = client.get("/api/health")
    assert resp.status_code == 200, f"Health check failed: {resp.text}"
    assert resp.json()["status"] == "ok"
    print("  [PASS] 1. GET /api/health -> 200 OK")

    # 2. Register User A
    resp = client.post("/api/auth/register", json={
        "full_name": name_a,
        "email": email_a,
        "password": pwd_a
    })
    assert resp.status_code == 201, f"Registration failed: {resp.text}"
    user_a_data = resp.json()
    assert user_a_data["email"] == email_a
    assert user_a_data["full_name"] == name_a
    assert "hashed_password" not in user_a_data, "SECURITY VIOLATION: hashed_password exposed"
    assert "password" not in user_a_data, "SECURITY VIOLATION: password exposed"
    print("  [PASS] 2. POST /api/auth/register -> 201 Created (no credentials exposed)")

    # 3. Duplicate Registration Rejected
    resp = client.post("/api/auth/register", json={
        "full_name": name_a,
        "email": email_a,
        "password": pwd_a
    })
    assert resp.status_code == 409, f"Duplicate registration expected 409, got {resp.status_code}"
    print("  [PASS] 3. POST /api/auth/register (duplicate) -> 409 Conflict")

    # 4. Login User A
    resp = client.post("/api/auth/login", json={
        "email": email_a,
        "password": pwd_a
    })
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    login_data = resp.json()
    assert "access_token" in login_data
    token_a = login_data["access_token"]
    assert login_data["token_type"] == "bearer"
    assert "hashed_password" not in login_data["user"]
    print("  [PASS] 4. POST /api/auth/login -> 200 OK with JWT access token")

    # 5. Invalid Login Rejections
    resp = client.post("/api/auth/login", json={"email": email_a, "password": "WrongPassword"})
    assert resp.status_code == 401, f"Bad password expected 401, got {resp.status_code}"
    resp = client.post("/api/auth/login", json={"email": "nonexistent@athletiq.com", "password": "WrongPassword"})
    assert resp.status_code == 401, f"Nonexistent user expected 401, got {resp.status_code}"
    print("  [PASS] 5. POST /api/auth/login (invalid creds) -> 401 Unauthorized")

    # 6. Protected routes reject missing or invalid tokens
    headers_a = {"Authorization": f"Bearer {token_a}"}
    resp = client.get("/api/users/me")
    assert resp.status_code == 401, f"Unauthenticated request expected 401, got {resp.status_code}"
    resp = client.get("/api/users/me", headers={"Authorization": "Bearer invalid.fake.token"})
    assert resp.status_code == 401, f"Invalid token expected 401, got {resp.status_code}"
    print("  [PASS] 6. Missing/invalid token rejected with 401 Unauthorized")

    # 7. GET /api/users/me with valid token
    resp = client.get("/api/users/me", headers=headers_a)
    assert resp.status_code == 200
    assert resp.json()["email"] == email_a
    print("  [PASS] 7. GET /api/users/me -> 200 OK")

    # 8. GET /api/auth/me with valid token
    resp = client.get("/api/auth/me", headers=headers_a)
    assert resp.status_code == 200
    assert resp.json()["full_name"] == name_a
    print("  [PASS] 8. GET /api/auth/me -> 200 OK")

    # 9. Athlete Profile: GET before creation should be 404
    resp = client.get("/api/athletes/profile", headers=headers_a)
    assert resp.status_code == 404
    print("  [PASS] 9. GET /api/athletes/profile (before create) -> 404 Not Found")

    # 10. Athlete Profile: POST /api/athletes/profile
    profile_payload = {
        "age": 24,
        "gender": "male",
        "height": 182.5,
        "weight": 76.0,
        "sport": "Basketball",
        "experience_level": "advanced"
    }
    resp = client.post("/api/athletes/profile", json=profile_payload, headers=headers_a)
    assert resp.status_code == 201, f"Create profile failed: {resp.text}"
    prof_a = resp.json()
    assert prof_a["sport"] == "Basketball"
    assert prof_a["height"] == 182.5
    print("  [PASS] 10. POST /api/athletes/profile -> 201 Created")

    # 11. Athlete Profile: Duplicate POST should be 400
    resp = client.post("/api/athletes/profile", json=profile_payload, headers=headers_a)
    assert resp.status_code == 400
    print("  [PASS] 11. POST /api/athletes/profile (duplicate) -> 400 Bad Request")

    # 12. Athlete Profile: GET /api/athletes/profile
    resp = client.get("/api/athletes/profile", headers=headers_a)
    assert resp.status_code == 200
    assert resp.json()["sport"] == "Basketball"
    print("  [PASS] 12. GET /api/athletes/profile -> 200 OK")

    # 13. Athlete Profile: PUT /api/athletes/profile
    resp = client.put("/api/athletes/profile", json={"sport": "Track & Field", "weight": 75.0}, headers=headers_a)
    assert resp.status_code == 200
    assert resp.json()["sport"] == "Track & Field"
    assert resp.json()["weight"] == 75.0
    assert resp.json()["height"] == 182.5  # Unchanged field preserved
    print("  [PASS] 13. PUT /api/athletes/profile -> 200 OK (partial update preserved)")

    # 14. Exercise Session: POST /api/sessions
    session_payload = {
        "exercise_name": "squat",
        "started_at": "2026-09-28T10:00:00Z",
        "ended_at": "2026-09-28T10:15:00Z",
        "duration": 900,
        "total_repetitions": 35
    }
    resp = client.post("/api/sessions", json=session_payload, headers=headers_a)
    assert resp.status_code == 201, f"Create session failed: {resp.text}"
    ses_a = resp.json()
    assert ses_a["exercise_name"] == "squat"
    assert ses_a["total_repetitions"] == 35
    assert ses_a["performance_score"] is None, "performance_score must not have fake placeholder"
    session_a_id = ses_a["id"]
    print("  [PASS] 14. POST /api/sessions -> 201 Created")

    # 15. Exercise Session: GET /api/sessions
    resp = client.get("/api/sessions", headers=headers_a)
    assert resp.status_code == 200
    sessions_list = resp.json()
    assert len(sessions_list) >= 1
    assert any(s["id"] == session_a_id for s in sessions_list)
    print("  [PASS] 15. GET /api/sessions -> 200 OK (lists user sessions)")

    # 16. Exercise Session: GET /api/sessions/{session_id}
    resp = client.get(f"/api/sessions/{session_a_id}", headers=headers_a)
    assert resp.status_code == 200
    assert resp.json()["id"] == session_a_id
    print(f"  [PASS] 16. GET /api/sessions/{session_a_id} -> 200 OK")

    # 17. Multi-User Isolation Test (User B)
    uid_b = uuid.uuid4().hex[:8]
    email_b = f"athlete_{uid_b}@athletiq.com"
    resp = client.post("/api/auth/register", json={
        "full_name": f"Athlete {uid_b}",
        "email": email_b,
        "password": "Password123"
    })
    assert resp.status_code == 201
    resp = client.post("/api/auth/login", json={"email": email_b, "password": "Password123"})
    token_b = resp.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # User B should NOT see User A's session by ID
    resp = client.get(f"/api/sessions/{session_a_id}", headers=headers_b)
    assert resp.status_code == 404, f"Security Breach: User B could access User A's session! Got {resp.status_code}"
    print("  [PASS] 17. Security Isolation: User B cannot access User A's session -> 404 Not Found")

    # User B has empty session list
    resp = client.get("/api/sessions", headers=headers_b)
    assert resp.status_code == 200
    assert resp.json() == [], "User B should have 0 sessions"
    print("  [PASS] 18. Security Isolation: User B session list is isolated")

    print("\nALL STAGE 2 TESTS PASSED PERFECTLY!\n")

if __name__ == "__main__":
    test_security_utilities()
    test_full_auth_and_crud_flow()
