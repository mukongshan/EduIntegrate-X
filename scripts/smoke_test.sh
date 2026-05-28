#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_DIR="$ROOT_DIR/tmp/smoke"
API_KEY="${VITE_INTEGRATION_API_KEY:-integration-server-api-key-2026}"

mkdir -p "$TMP_DIR"

require_contains() {
  local file="$1"
  local text="$2"
  local label="$3"
  if ! grep -q "$text" "$file"; then
    echo "Smoke check failed: $label"
    echo "Response was:"
    cat "$file"
    exit 1
  fi
}

xml_text() {
  local file="$1"
  local path="$2"
  python - "$file" "$path" <<'PY'
import sys
import xml.etree.ElementTree as ET

file_path, path = sys.argv[1], sys.argv[2]
root = ET.parse(file_path).getroot()
node = root
for part in path.split("/"):
    node = node.find(part)
    if node is None:
        print("")
        raise SystemExit
print((node.text or "").strip())
PY
}

xml_count() {
  local file="$1"
  local path="$2"
  python - "$file" "$path" <<'PY'
import sys
import xml.etree.ElementTree as ET

file_path, path = sys.argv[1], sys.argv[2]
root = ET.parse(file_path).getroot()
print(len(root.findall(path)))
PY
}

xml_college_value() {
  local file="$1"
  local college="$2"
  local field="$3"
  python - "$file" "$college" "$field" <<'PY'
import sys
import xml.etree.ElementTree as ET

file_path, college, field = sys.argv[1], sys.argv[2], sys.argv[3]
root = ET.parse(file_path).getroot()
for item in root.findall("data/Summary/college"):
    if (item.findtext("collegeId") or "").strip() == college:
        print((item.findtext(field) or "").strip())
        raise SystemExit
print("")
PY
}

require_equals() {
  local actual="$1"
  local expected="$2"
  local label="$3"
  if [ "$actual" != "$expected" ]; then
    echo "Smoke check failed: $label (expected $expected, got $actual)"
    exit 1
  fi
}

echo "Checking health endpoints..."
curl -fsS http://localhost:8000/health >/dev/null
curl -fsS http://localhost:8001/health >/dev/null
curl -fsS http://localhost:8002/health >/dev/null
curl -fsS http://localhost:8081/health >/dev/null

echo "Checking demo data scale..."
for item in A:8000 B:8001 C:8002; do
  college="${item%%:*}"
  port="${item##*:}"
  curl -fsS "http://localhost:$port/api/v1/courses" >"$TMP_DIR/courses_$college.xml"
  require_equals "$(xml_count "$TMP_DIR/courses_$college.xml" "data/courses/course")" "10" "$college course count"

  curl -fsS "http://localhost:$port/internal/v1/stats/summary" >"$TMP_DIR/stats_$college.xml"
  require_equals "$(xml_text "$TMP_DIR/stats_$college.xml" "data/summary/studentCount")" "50" "$college student count"
  require_equals "$(xml_text "$TMP_DIR/stats_$college.xml" "data/summary/courseCount")" "10" "$college course stats count"
  require_equals "$(xml_text "$TMP_DIR/stats_$college.xml" "data/summary/enrollmentCount")" "250" "$college enrollment count"
done

echo "Checking shared courses..."
curl -fsS http://localhost:8081/api/v1/shared-courses >"$TMP_DIR/shared.xml"
require_contains "$TMP_DIR/shared.xml" "<collegeId>B</collegeId>" "shared courses include B collegeId"
require_contains "$TMP_DIR/shared.xml" "<id>B001</id>" "shared courses include B001"

echo "Submitting cross-college enrollment A -> B..."
curl -fsS -X POST http://localhost:8081/api/v1/enrollments \
  -H "Content-Type: application/xml" \
  -H "Accept: application/xml" \
  --data-binary @- >"$TMP_DIR/enroll.xml" <<'XML'
<EnrollmentRequest>
  <meta>
    <homeCollegeId>A</homeCollegeId>
    <targetCollegeId>B</targetCollegeId>
    <requestTime>2026-05-28 20:00:00</requestTime>
  </meta>
  <choices>
    <choice>
      <sid>S2024001</sid>
      <cid>B001</cid>
      <score>0</score>
    </choice>
  </choices>
</EnrollmentRequest>
XML

require_contains "$TMP_DIR/enroll.xml" "<code>0</code>" "enrollment accepted"
require_contains "$TMP_DIR/enroll.xml" "<status>ENROLLED</status>" "enrollment writeback completed"
enrollment_id="$(xml_text "$TMP_DIR/enroll.xml" "data/enrollmentId")"
if [ -z "$enrollment_id" ]; then
  echo "Smoke check failed: missing enrollmentId"
  cat "$TMP_DIR/enroll.xml"
  exit 1
fi

echo "Checking student enrollment list..."
curl -fsS http://localhost:8081/api/v1/students/S2024001/enrollments >"$TMP_DIR/list.xml"
require_contains "$TMP_DIR/list.xml" "$enrollment_id" "student enrollment list contains new enrollment"
require_contains "$TMP_DIR/list.xml" "<cid>B001</cid>" "student enrollment list contains course B001"

echo "Withdrawing enrollment..."
curl -fsS -X POST "http://localhost:8081/api/v1/enrollments/$enrollment_id/withdraw" \
  -H "Content-Type: application/xml" \
  -H "Accept: application/xml" \
  --data-binary @- >"$TMP_DIR/withdraw.xml" <<XML
<WithdrawRequest>
  <meta>
    <requestTime>2026-05-28 20:05:00</requestTime>
  </meta>
  <choices>
    <choice>
      <sid>S2024001</sid>
      <cid>B001</cid>
      <score>0</score>
    </choice>
  </choices>
</WithdrawRequest>
XML

require_contains "$TMP_DIR/withdraw.xml" "<code>0</code>" "withdraw accepted"
require_contains "$TMP_DIR/withdraw.xml" "<status>WITHDRAWN</status>" "withdraw writeback completed"

curl -fsS http://localhost:8081/api/v1/students/S2024001/enrollments >"$TMP_DIR/list_after_withdraw.xml"
if grep -q "$enrollment_id" "$TMP_DIR/list_after_withdraw.xml"; then
  echo "Smoke check failed: withdrawn enrollment still appears in student list"
  cat "$TMP_DIR/list_after_withdraw.xml"
  exit 1
fi

echo "Checking stats..."
curl -fsS http://localhost:8081/api/v1/stats/summary \
  -H "Accept: application/xml" \
  -H "Authorization: Bearer $API_KEY" >"$TMP_DIR/stats.xml"
require_contains "$TMP_DIR/stats.xml" "<code>0</code>" "stats response success"
require_contains "$TMP_DIR/stats.xml" "<collegeId>B</collegeId>" "stats include college B"
for college in A B C; do
  require_equals "$(xml_college_value "$TMP_DIR/stats.xml" "$college" "studentCount")" "50" "integration $college student count"
  require_equals "$(xml_college_value "$TMP_DIR/stats.xml" "$college" "courseCount")" "10" "integration $college course count"
  require_equals "$(xml_college_value "$TMP_DIR/stats.xml" "$college" "enrollmentCount")" "250" "integration $college enrollment count"
done
require_equals "$(xml_text "$TMP_DIR/stats.xml" "data/Summary/total/studentCount")" "150" "integration total student count"
require_equals "$(xml_text "$TMP_DIR/stats.xml" "data/Summary/total/courseCount")" "30" "integration total course count"
require_equals "$(xml_text "$TMP_DIR/stats.xml" "data/Summary/total/enrollmentCount")" "750" "integration total enrollment count"

echo "Smoke test passed."
