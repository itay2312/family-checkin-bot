from typing import Any, Dict, List
import json

def fmt_dt(dt):
    if not dt:
        return ""
    if isinstance(dt, str):
        return dt
    return dt.strftime("%Y-%m-%d %H:%M:%S UTC")

def status_badge(status: str) -> str:
    s = (status or "UNKNOWN").upper()
    if s == "OK":
        return '<span class="px-2 py-1 rounded-full text-xs bg-green-100 text-green-800">OK</span>'
    if s == "HELP":
        return '<span class="px-2 py-1 rounded-full text-xs bg-red-100 text-red-800">HELP</span>'
    return '<span class="px-2 py-1 rounded-full text-xs bg-gray-100 text-gray-800">UNKNOWN</span>'

def admin_page(members: List[Dict[str, Any]], events: List[Dict[str, Any]], base_url: str, token: str) -> str:
    ok_count = sum(1 for m in members if (m.get("last_status") or "").upper() == "OK")
    help_count = sum(1 for m in members if (m.get("last_status") or "").upper() == "HELP")
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <script src="https://cdn.tailwindcss.com"></script>
  <title>Family Check-in Admin</title>
</head>
<body class="bg-slate-50 text-slate-900">
  <div class="max-w-5xl mx-auto p-4 sm:p-6">
    <div class="flex items-start justify-between gap-4">
      <div>
        <h1 class="text-2xl sm:text-3xl font-bold">Family Check-in Admin</h1>
        <p class="text-sm text-slate-600 mt-1">Live status dashboard (Telegram check-ins)</p>
      </div>
      <div class="flex flex-col items-end gap-2">
        <a class="text-sm underline text-slate-700" href="{base_url}/health" target="_blank">/health</a>
        <button id="testBtn" class="px-4 py-2 rounded-xl bg-slate-900 text-white text-sm hover:bg-slate-800">
          Send TEST check-in
        </button>
      </div>
    </div>

    <div class="mt-6 grid grid-cols-1 sm:grid-cols-3 gap-3">
      <div class="bg-white rounded-2xl shadow-sm p-4 border">
        <div class="text-sm text-slate-600">Members</div>
        <div class="text-2xl font-semibold">{len(members)}</div>
      </div>
      <div class="bg-white rounded-2xl shadow-sm p-4 border">
        <div class="text-sm text-slate-600">OK</div>
        <div class="text-2xl font-semibold">{ok_count}</div>
      </div>
      <div class="bg-white rounded-2xl shadow-sm p-4 border">
        <div class="text-sm text-slate-600">Need help</div>
        <div class="text-2xl font-semibold">{help_count}</div>
      </div>
    </div>

    <div class="mt-6 bg-white rounded-2xl shadow-sm border overflow-hidden">
      <div class="p-4 border-b">
        <h2 class="font-semibold">Members</h2>
        <p class="text-sm text-slate-600">Updates when buttons are pressed.</p>
      </div>
      <div class="overflow-x-auto">
        <table class="min-w-full text-sm">
          <thead class="bg-slate-50 text-slate-600">
            <tr>
              <th class="text-left p-3">Name</th>
              <th class="text-left p-3">Status</th>
              <th class="text-left p-3">Last event</th>
              <th class="text-left p-3">Updated</th>
            </tr>
          </thead>
          <tbody>
            {''.join(f"""<tr class='border-t hover:bg-slate-50'>
              <td class='p-3 font-medium'>{m.get('display_name','')}</td>
              <td class='p-3'>{status_badge(m.get('last_status'))}</td>
              <td class='p-3'>{m.get('last_checkin_event_id') or ''}</td>
              <td class='p-3 text-slate-600'>{fmt_dt(m.get('updated_at'))}</td>
            </tr>""" for m in members)}
          </tbody>
        </table>
      </div>
    </div>

    <div class="mt-6 bg-white rounded-2xl shadow-sm border overflow-hidden">
      <div class="p-4 border-b">
        <h2 class="font-semibold">Recent events</h2>
      </div>
      <div class="overflow-x-auto">
        <table class="min-w-full text-sm">
          <thead class="bg-slate-50 text-slate-600">
            <tr>
              <th class="text-left p-3">Event ID</th>
              <th class="text-left p-3">Started</th>
              <th class="text-left p-3">Last alert</th>
              <th class="text-left p-3">Cleared</th>
              <th class="text-left p-3">Active</th>
            </tr>
          </thead>
          <tbody>
            {''.join(f"""<tr class='border-t hover:bg-slate-50'>
              <td class='p-3 font-medium'>{e.get('id')}</td>
              <td class='p-3'>{fmt_dt(e.get('started_at'))}</td>
              <td class='p-3'>{fmt_dt(e.get('last_alert_at'))}</td>
              <td class='p-3'>{fmt_dt(e.get('cleared_at'))}</td>
              <td class='p-3'>{'✅' if e.get('is_active') else ''}</td>
            </tr>""" for e in events)}
          </tbody>
        </table>
      </div>
    </div>

    <div class="mt-6 text-xs text-slate-500">Admin URL includes a token. Keep it private.</div>
  </div>

<script>
const token = {json.dumps(token)};
const baseUrl = {json.dumps(base_url)};
document.getElementById('testBtn').addEventListener('click', async () => {{
  try {{
    const r = await fetch(`${{baseUrl}}/admin/send_test_checkin?token=${{encodeURIComponent(token)}}`, {{ method: 'POST' }});
    if (!r.ok) throw new Error('Failed');
    alert('Sent test check-in 👍');
    location.reload();
  }} catch (e) {{
    alert('Could not send test check-in. Check server logs and ADMIN_TOKEN.');
  }}
}});
</script>
</body>
</html>"""
