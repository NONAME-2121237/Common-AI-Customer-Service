from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.auth.routes import get_current_user

router = APIRouter(prefix="/kb", tags=["knowledge"])

KB_CONFIG_PAGE = """
<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>知识库配置</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        .header { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 20px; }
        .header h1 { color: #333; font-size: 24px; }
        .card { background: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); padding: 20px; margin-bottom: 20px; }
        .card h2 { color: #333; font-size: 18px; margin-bottom: 15px; border-bottom: 2px solid #3b82f6; padding-bottom: 10px; }
        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; margin-bottom: 5px; color: #666; font-weight: 500; }
        .form-group input, .form-group textarea, .form-group select { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px; }
        .form-group textarea { min-height: 100px; resize: vertical; }
        .btn { padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; font-size: 14px; }
        .btn-primary { background: #3b82f6; color: white; }
        .btn-primary:hover { background: #2563eb; }
        .btn-success { background: #10b981; color: white; }
        .btn-danger { background: #ef4444; color: white; }
        .btn-sm { padding: 5px 10px; font-size: 12px; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #eee; }
        th { background: #f8f9fa; font-weight: 600; color: #333; }
        .status { display: inline-block; padding: 4px 8px; border-radius: 4px; font-size: 12px; }
        .status.active { background: #d1fae5; color: #065f46; }
        .status.inactive { background: #fee2e2; color: #991b1b; }
        .actions { display: flex; gap: 5px; }
        .tab-nav { display: flex; gap: 10px; margin-bottom: 20px; }
        .tab { padding: 10px 20px; background: #e5e7eb; border-radius: 4px; cursor: pointer; }
        .tab.active { background: #3b82f6; color: white; }
        .alert { padding: 15px; border-radius: 4px; margin-bottom: 15px; }
        .alert-success { background: #d1fae5; color: #065f46; }
        .alert-error { background: #fee2e2; color: #991b1b; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🧠 知识库配置</h1>
        </div>

        <div class="tab-nav">
            <div class="tab active" onclick="switchTab('documents')">📄 文档管理</div>
            <div class="tab" onclick="switchTab('config')">⚙️ 配置设置</div>
            <div class="tab" onclick="switchTab('test')">🧪 测试查询</div>
        </div>

        <div id="documents" class="card">
            <h2>文档列表</h2>
            <div id="alert-doc"></div>
            <button class="btn btn-primary" onclick="showAddDoc()">+ 添加文档</button>
            <div style="margin-top: 15px;">
                <table>
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>标题</th>
                            <th>类型</th>
                            <th>状态</th>
                            <th>创建时间</th>
                            <th>操作</th>
                        </tr>
                    </thead>
                    <tbody id="doc-list"></tbody>
                </table>
            </div>
        </div>

        <div id="config" class="card" style="display:none;">
            <h2>知识库配置</h2>
            <div id="alert-config"></div>
            <div class="form-group">
                <label>向量模型</label>
                <select id="vector-model">
                    <option value="openai">OpenAI Ada002</option>
                    <option value="bge">BGE Large</option>
                    <option value="m3e">M3E</option>
                </select>
            </div>
            <div class="form-group">
                <label>检索模式</label>
                <select id="retrieve-mode">
                    <option value="similarity">相似度搜索</option>
                    <option value="mmr">最大边际相关性</option>
                    <option value="hybrid">混合搜索</option>
                </select>
            </div>
            <div class="form-group">
                <label>Top-K 检索数量</label>
                <input type="number" id="top-k" value="5" min="1" max="20">
            </div>
            <div class="form-group">
                <label>相似度阈值</label>
                <input type="number" id="similarity-threshold" value="0.7" step="0.1" min="0" max="1">
            </div>
            <button class="btn btn-primary" onclick="saveConfig()">保存配置</button>
        </div>

        <div id="test" class="card" style="display:none;">
            <h2>测试查询</h2>
            <div id="alert-test"></div>
            <div class="form-group">
                <label>查询内容</label>
                <textarea id="test-query" placeholder="输入要查询的内容..."></textarea>
            </div>
            <button class="btn btn-primary" onclick="testQuery()">🔍 执行查询</button>
            <div id="test-results" style="margin-top: 20px;"></div>
        </div>

        <div id="doc-modal" style="display:none; position:fixed; top:0; left:0; right:0; bottom:0; background:rgba(0,0,0,0.5); z-index:1000;">
            <div style="background:white; max-width:600px; margin:50px auto; padding:20px; border-radius:8px;">
                <h2 id="modal-title">添加文档</h2>
                <div id="alert-modal"></div>
                <input type="hidden" id="doc-id">
                <div class="form-group">
                    <label>标题</label>
                    <input type="text" id="doc-title" placeholder="文档标题">
                </div>
                <div class="form-group">
                    <label>内容</label>
                    <textarea id="doc-content" placeholder="文档内容"></textarea>
                </div>
                <div class="form-group">
                    <label>类型</label>
                    <select id="doc-type">
                        <option value="faq">FAQ</option>
                        <option value="manual">使用手册</option>
                        <option value="policy">政策文档</option>
                        <option value="other">其他</option>
                    </select>
                </div>
                <div style="display:flex; gap:10px; justify-content:flex-end;">
                    <button class="btn" onclick="closeModal()">取消</button>
                    <button class="btn btn-primary" onclick="saveDoc()">保存</button>
                </div>
            </div>
        </div>
    </div>

    <script>
        const API_BASE = '/api';

        async function makeRequest(url, method, body) {
            const token = localStorage.getItem('token');
            const headers = { 'Content-Type': 'application/json' };
            if (token) headers['Authorization'] = `Bearer ${token}`;

            const res = await fetch(API_BASE + url, {
                method,
                headers,
                body: body ? JSON.stringify(body) : undefined
            });
            if (!res.ok) {
                const err = await res.json().catch(() => ({ detail: 'Request failed' }));
                throw new Error(err.detail || 'Request failed');
            }
            return res.json();
        }

        function switchTab(tab) {
            document.querySelectorAll('.card').forEach(c => c.style.display = 'none');
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.getElementById(tab).style.display = 'block';
            event.target.classList.add('active');
            if (tab === 'documents') loadDocs();
            if (tab === 'config') loadConfig();
        }

        function showAlert(id, msg, type) {
            document.getElementById(id).innerHTML = `<div class="alert alert-${type}">${msg}</div>`;
            setTimeout(() => document.getElementById(id).innerHTML = '', 3000);
        }

        async function loadDocs() {
            try {
                const data = await makeRequest('/kb/documents', 'GET');
                const tbody = document.getElementById('doc-list');
                if (!data.documents || data.documents.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:#999;">暂无文档</td></tr>';
                    return;
                }
                tbody.innerHTML = data.documents.map(doc => `
                    <tr>
                        <td>${doc.id}</td>
                        <td>${doc.title}</td>
                        <td>${doc.type}</td>
                        <td><span class="status ${doc.active ? 'active' : 'inactive'}">${doc.active ? '启用' : '禁用'}</span></td>
                        <td>${new Date(doc.created_at * 1000).toLocaleString()}</td>
                        <td class="actions">
                            <button class="btn btn-sm btn-primary" onclick="editDoc('${doc.id}')">编辑</button>
                            <button class="btn btn-sm btn-danger" onclick="deleteDoc('${doc.id}')">删除</button>
                        </td>
                    </tr>
                `).join('');
            } catch (e) {
                showAlert('alert-doc', '加载文档失败: ' + e.message, 'error');
            }
        }

        async function loadConfig() {
            try {
                const data = await makeRequest('/kb/config', 'GET');
                document.getElementById('vector-model').value = data.vector_model || 'openai';
                document.getElementById('retrieve-mode').value = data.retrieve_mode || 'similarity';
                document.getElementById('top-k').value = data.top_k || 5;
                document.getElementById('similarity-threshold').value = data.similarity_threshold || 0.7;
            } catch (e) {
                showAlert('alert-config', '加载配置失败: ' + e.message, 'error');
            }
        }

        function showAddDoc() {
            document.getElementById('modal-title').textContent = '添加文档';
            document.getElementById('doc-id').value = '';
            document.getElementById('doc-title').value = '';
            document.getElementById('doc-content').value = '';
            document.getElementById('doc-type').value = 'faq';
            document.getElementById('doc-modal').style.display = 'block';
        }

        async function editDoc(id) {
            try {
                const data = await makeRequest(`/kb/documents/${id}`, 'GET');
                document.getElementById('modal-title').textContent = '编辑文档';
                document.getElementById('doc-id').value = id;
                document.getElementById('doc-title').value = data.title;
                document.getElementById('doc-content').value = data.content;
                document.getElementById('doc-type').value = data.type;
                document.getElementById('doc-modal').style.display = 'block';
            } catch (e) {
                showAlert('alert-doc', '编辑失败: ' + e.message, 'error');
            }
        }

        function closeModal() {
            document.getElementById('doc-modal').style.display = 'none';
        }

        async function saveDoc() {
            const id = document.getElementById('doc-id').value;
            const doc = {
                title: document.getElementById('doc-title').value,
                content: document.getElementById('doc-content').value,
                type: document.getElementById('doc-type').value
            };
            try {
                if (id) {
                    await makeRequest(`/kb/documents/${id}`, 'PUT', doc);
                    showAlert('alert-doc', '文档更新成功', 'success');
                } else {
                    await makeRequest('/kb/documents', 'POST', doc);
                    showAlert('alert-doc', '文档添加成功', 'success');
                }
                closeModal();
                loadDocs();
            } catch (e) {
                showAlert('alert-modal', '保存失败: ' + e.message, 'error');
            }
        }

        async function deleteDoc(id) {
            if (!confirm('确定要删除这个文档吗？')) return;
            try {
                await makeRequest(`/kb/documents/${id}`, 'DELETE');
                showAlert('alert-doc', '文档删除成功', 'success');
                loadDocs();
            } catch (e) {
                showAlert('alert-doc', '删除失败: ' + e.message, 'error');
            }
        }

        async function saveConfig() {
            const config = {
                vector_model: document.getElementById('vector-model').value,
                retrieve_mode: document.getElementById('retrieve-mode').value,
                top_k: parseInt(document.getElementById('top-k').value),
                similarity_threshold: parseFloat(document.getElementById('similarity-threshold').value)
            };
            try {
                await makeRequest('/kb/config', 'PUT', config);
                showAlert('alert-config', '配置保存成功', 'success');
            } catch (e) {
                showAlert('alert-config', '保存失败: ' + e.message, 'error');
            }
        }

        async function testQuery() {
            const query = document.getElementById('test-query').value.trim();
            if (!query) {
                showAlert('alert-test', '请输入查询内容', 'error');
                return;
            }
            try {
                const data = await makeRequest('/kb/query', 'POST', { query, top_k: 3 });
                const results = document.getElementById('test-results');
                if (!data.results || data.results.length === 0) {
                    results.innerHTML = '<p style="color:#999;">没有找到相关结果</p>';
                    return;
                }
                results.innerHTML = '<h3 style="margin-bottom:10px;">查询结果:</h3>' + data.results.map(r => `
                    <div style="background:#f8f9fa; padding:15px; border-radius:4px; margin-bottom:10px;">
                        <p><strong>${r.title}</strong> (相似度: ${(r.score * 100).toFixed(1)}%)</p>
                        <p style="margin-top:5px; color:#666;">${r.content}</p>
                    </div>
                `).join('');
            } catch (e) {
                showAlert('alert-test', '查询失败: ' + e.message, 'error');
            }
        }

        loadDocs();
    </script>
</body>
</html>
"""


class KBDocument(BaseModel):
    title: str
    content: str
    type: str = "faq"
    active: bool = True


class KBConfig(BaseModel):
    vector_model: str = "openai"
    retrieve_mode: str = "similarity"
    top_k: int = 5
    similarity_threshold: float = 0.7


class KBQueryRequest(BaseModel):
    query: str
    top_k: int = 3


_kb_documents: Dict[str, Dict[str, Any]] = {
    "doc1": {
        "id": "doc1",
        "title": "常见问题FAQ",
        "content": "欢迎使用智能客服系统。常见问题包括：如何重置密码、如何联系人工客服、如何查看会话历史等。",
        "type": "faq",
        "active": True,
        "created_at": 1704067200
    },
    "doc2": {
        "id": "doc2",
        "title": "使用手册",
        "content": "本系统支持多语言界面，您可以点击右上角切换中文、英文或日文。系统会自动保存您的会话记录。",
        "type": "manual",
        "active": True,
        "created_at": 1704153600
    }
}

_kb_config = KBConfig()


@router.get("")
async def kb_home(current_user: dict = Depends(get_current_user)):
    return HTMLResponse(KB_CONFIG_PAGE)


@router.get("/documents")
async def list_documents(current_user: dict = Depends(get_current_user)):
    docs = [doc for doc in _kb_documents.values() if doc["active"]]
    return {"documents": docs, "count": len(docs)}


@router.get("/documents/{doc_id}")
async def get_document(doc_id: str, current_user: dict = Depends(get_current_user)):
    if doc_id not in _kb_documents:
        raise HTTPException(status_code=404, detail="Document not found")
    return _kb_documents[doc_id]


@router.post("/documents")
async def create_document(doc: KBDocument, current_user: dict = Depends(get_current_user)):
    import time
    doc_id = f"doc{int(time.time() * 1000)}"
    _kb_documents[doc_id] = {
        "id": doc_id,
        "title": doc.title,
        "content": doc.content,
        "type": doc.type,
        "active": doc.active,
        "created_at": int(time.time())
    }
    return {"id": doc_id, "status": "created"}


@router.put("/documents/{doc_id}")
async def update_document(doc_id: str, doc: KBDocument, current_user: dict = Depends(get_current_user)):
    if doc_id not in _kb_documents:
        raise HTTPException(status_code=404, detail="Document not found")
    _kb_documents[doc_id].update({
        "title": doc.title,
        "content": doc.content,
        "type": doc.type,
        "active": doc.active
    })
    return {"id": doc_id, "status": "updated"}


@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str, current_user: dict = Depends(get_current_user)):
    if doc_id not in _kb_documents:
        raise HTTPException(status_code=404, detail="Document not found")
    _kb_documents[doc_id]["active"] = False
    return {"id": doc_id, "status": "deleted"}


@router.get("/config")
async def get_kb_config(current_user: dict = Depends(get_current_user)):
    return {
        "vector_model": _kb_config.vector_model,
        "retrieve_mode": _kb_config.retrieve_mode,
        "top_k": _kb_config.top_k,
        "similarity_threshold": _kb_config.similarity_threshold
    }


@router.put("/config")
async def update_kb_config(config: KBConfig, current_user: dict = Depends(get_current_user)):
    global _kb_config
    _kb_config = config
    return {"status": "success", "config": _kb_config}


@router.post("/query")
async def query_knowledge(request: KBQueryRequest, current_user: dict = Depends(get_current_user)):
    query = request.query.lower()
    results = []

    for doc in _kb_documents.values():
        if not doc["active"]:
            continue
        content_lower = doc["content"].lower()
        title_lower = doc["title"].lower()

        if query in content_lower or query in title_lower:
            score = 0.9
        elif any(word in content_lower or word in title_lower for word in query.split()):
            score = 0.7
        else:
            continue

        results.append({
            "id": doc["id"],
            "title": doc["title"],
            "content": doc["content"],
            "type": doc["type"],
            "score": score
        })

    results.sort(key=lambda x: x["score"], reverse=True)
    return {"results": results[:request.top_k]}
