import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { knowledgeApi } from '../services/knowledgeApi';

interface KBDocument {
  id: string;
  title: string;
  content: string;
  type: string;
  active: boolean;
  created_at: number;
}

interface KBConfig {
  vector_model: string;
  retrieve_mode: string;
  top_k: number;
  similarity_threshold: number;
}

const Knowledge: React.FC = () => {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState<'documents' | 'config' | 'test'>('documents');
  const [documents, setDocuments] = useState<KBDocument[]>([]);
  const [config, setConfig] = useState<KBConfig>({
    vector_model: 'openai',
    retrieve_mode: 'similarity',
    top_k: 5,
    similarity_threshold: 0.7
  });
  const [testQuery, setTestQuery] = useState('');
  const [testResults, setTestResults] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const [editingDoc, setEditingDoc] = useState<KBDocument | null>(null);
  const [docForm, setDocForm] = useState({ title: '', content: '', type: 'faq' });

  useEffect(() => {
    if (activeTab === 'documents') loadDocuments();
    if (activeTab === 'config') loadConfig();
  }, [activeTab]);

  const loadDocuments = async () => {
    setLoading(true);
    try {
      const data = await knowledgeApi.getDocuments();
      setDocuments(data.documents || []);
    } catch (e: any) {
      showMessage('error', e.message || t('common.error'));
    } finally {
      setLoading(false);
    }
  };

  const loadConfig = async () => {
    try {
      const data = await knowledgeApi.getConfig();
      setConfig(data);
    } catch (e: any) {
      console.error('Failed to load config:', e);
    }
  };

  const showMessage = (type: 'success' | 'error', text: string) => {
    setMessage({ type, text });
    setTimeout(() => setMessage(null), 3000);
  };

  const handleSaveConfig = async () => {
    try {
      await knowledgeApi.updateConfig(config);
      showMessage('success', t('common.success'));
    } catch (e: any) {
      showMessage('error', e.message || t('common.error'));
    }
  };

  const handleTestQuery = async () => {
    if (!testQuery.trim()) {
      showMessage('error', t('common.warning'));
      return;
    }
    setLoading(true);
    try {
      const results = await knowledgeApi.query(testQuery, 3);
      setTestResults(results.results || []);
    } catch (e: any) {
      showMessage('error', e.message || t('common.error'));
    } finally {
      setLoading(false);
    }
  };

  const handleAddDoc = () => {
    setEditingDoc(null);
    setDocForm({ title: '', content: '', type: 'faq' });
  };

  const handleEditDoc = (doc: KBDocument) => {
    setEditingDoc(doc);
    setDocForm({ title: doc.title, content: doc.content, type: doc.type });
  };

  const handleSaveDoc = async () => {
    try {
      if (editingDoc) {
        await knowledgeApi.updateDocument(editingDoc.id, docForm);
      } else {
        await knowledgeApi.createDocument(docForm);
      }
      showMessage('success', t('common.success'));
      loadDocuments();
      setEditingDoc(null);
    } catch (e: any) {
      showMessage('error', e.message || t('common.error'));
    }
  };

  const handleDeleteDoc = async (id: string) => {
    if (!confirm(t('users.confirmDelete'))) return;
    try {
      await knowledgeApi.deleteDocument(id);
      showMessage('success', t('common.success'));
      loadDocuments();
    } catch (e: any) {
      showMessage('error', e.message || t('common.error'));
    }
  };

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-lg shadow p-6">
        <h1 className="text-2xl font-bold mb-6">🧠 {t('menu.knowledge')}</h1>

        {message && (
          <div className={`mb-4 p-4 rounded ${message.type === 'success' ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'}`}>
            {message.text}
          </div>
        )}

        <div className="flex gap-2 mb-6">
          <button
            onClick={() => setActiveTab('documents')}
            className={`px-4 py-2 rounded ${activeTab === 'documents' ? 'bg-primary-600 text-white' : 'bg-gray-200'}`}
          >
            📄 {t('knowledge.documents')}
          </button>
          <button
            onClick={() => setActiveTab('config')}
            className={`px-4 py-2 rounded ${activeTab === 'config' ? 'bg-primary-600 text-white' : 'bg-gray-200'}`}
          >
            ⚙️ {t('knowledge.config')}
          </button>
          <button
            onClick={() => setActiveTab('test')}
            className={`px-4 py-2 rounded ${activeTab === 'test' ? 'bg-primary-600 text-white' : 'bg-gray-200'}`}
          >
            🧪 {t('knowledge.test')}
          </button>
        </div>

        {activeTab === 'documents' && (
          <div>
            <div className="flex justify-between mb-4">
              <button onClick={handleAddDoc} className="btn-primary">
                + {t('common.add')}
              </button>
            </div>

            {loading ? (
              <div className="text-center py-8 text-gray-500">{t('common.loading')}</div>
            ) : documents.length === 0 ? (
              <div className="text-center py-8 text-gray-500">{t('common.noData')}</div>
            ) : (
              <table className="w-full">
                <thead>
                  <tr className="text-left border-b">
                    <th className="pb-2">ID</th>
                    <th className="pb-2">{t('knowledge.title')}</th>
                    <th className="pb-2">{t('knowledge.type')}</th>
                    <th className="pb-2">{t('users.status')}</th>
                    <th className="pb-2">{t('users.createdAt')}</th>
                    <th className="pb-2">{t('common.actions')}</th>
                  </tr>
                </thead>
                <tbody>
                  {documents.map((doc) => (
                    <tr key={doc.id} className="border-b">
                      <td className="py-3 text-sm text-gray-500">{doc.id.substring(0, 8)}</td>
                      <td className="py-3">{doc.title}</td>
                      <td className="py-3">
                        <span className="px-2 py-1 bg-gray-100 rounded text-sm">{doc.type}</span>
                      </td>
                      <td className="py-3">
                        <span className={`px-2 py-1 rounded text-sm ${doc.active ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                          {doc.active ? t('users.enabled') : t('users.disabled')}
                        </span>
                      </td>
                      <td className="py-3 text-sm text-gray-500">
                        {new Date(doc.created_at * 1000).toLocaleDateString()}
                      </td>
                      <td className="py-3">
                        <button onClick={() => handleEditDoc(doc)} className="text-blue-600 hover:underline mr-3">
                          {t('common.edit')}
                        </button>
                        <button onClick={() => handleDeleteDoc(doc.id)} className="text-red-600 hover:underline">
                          {t('common.delete')}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}

        {activeTab === 'config' && (
          <div className="max-w-md space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">{t('knowledge.vectorModel')}</label>
              <select
                value={config.vector_model}
                onChange={(e) => setConfig({ ...config, vector_model: e.target.value })}
                className="w-full px-3 py-2 border rounded"
              >
                <option value="openai">OpenAI Ada002</option>
                <option value="bge">BGE Large</option>
                <option value="m3e">M3E</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">{t('knowledge.retrieveMode')}</label>
              <select
                value={config.retrieve_mode}
                onChange={(e) => setConfig({ ...config, retrieve_mode: e.target.value })}
                className="w-full px-3 py-2 border rounded"
              >
                <option value="similarity">{t('knowledge.similarity')}</option>
                <option value="mmr">MMR</option>
                <option value="hybrid">{t('knowledge.hybrid')}</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">{t('knowledge.topK')}</label>
              <input
                type="number"
                value={config.top_k}
                onChange={(e) => setConfig({ ...config, top_k: parseInt(e.target.value) || 5 })}
                className="w-full px-3 py-2 border rounded"
                min={1}
                max={20}
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">{t('knowledge.threshold')}</label>
              <input
                type="number"
                step="0.1"
                value={config.similarity_threshold}
                onChange={(e) => setConfig({ ...config, similarity_threshold: parseFloat(e.target.value) || 0.7 })}
                className="w-full px-3 py-2 border rounded"
                min={0}
                max={1}
              />
            </div>

            <button onClick={handleSaveConfig} className="btn-primary">
              {t('common.save')}
            </button>
          </div>
        )}

        {activeTab === 'test' && (
          <div>
            <div className="mb-4">
              <label className="block text-sm font-medium mb-1">{t('knowledge.query')}</label>
              <textarea
                value={testQuery}
                onChange={(e) => setTestQuery(e.target.value)}
                className="w-full px-3 py-2 border rounded h-24"
                placeholder={t('knowledge.queryPlaceholder')}
              />
            </div>
            <button onClick={handleTestQuery} disabled={loading} className="btn-primary">
              🔍 {t('common.search')}
            </button>

            {testResults.length > 0 && (
              <div className="mt-6">
                <h3 className="font-medium mb-3">{t('knowledge.results')}:</h3>
                {testResults.map((result, idx) => (
                  <div key={idx} className="bg-gray-50 p-4 rounded mb-3">
                    <div className="flex justify-between items-start mb-2">
                      <strong>{result.title}</strong>
                      <span className="text-sm text-gray-500">
                        {(result.score * 100).toFixed(1)}%
                      </span>
                    </div>
                    <p className="text-gray-600 text-sm">{result.content}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {editingDoc !== null && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-lg">
            <h2 className="text-xl font-bold mb-4">
              {editingDoc ? t('common.edit') : t('common.add')} {t('knowledge.document')}
            </h2>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">{t('knowledge.title')}</label>
                <input
                  type="text"
                  value={docForm.title}
                  onChange={(e) => setDocForm({ ...docForm, title: e.target.value })}
                  className="w-full px-3 py-2 border rounded"
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">{t('knowledge.content')}</label>
                <textarea
                  value={docForm.content}
                  onChange={(e) => setDocForm({ ...docForm, content: e.target.value })}
                  className="w-full px-3 py-2 border rounded h-32"
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">{t('knowledge.type')}</label>
                <select
                  value={docForm.type}
                  onChange={(e) => setDocForm({ ...docForm, type: e.target.value })}
                  className="w-full px-3 py-2 border rounded"
                >
                  <option value="faq">FAQ</option>
                  <option value="manual">{t('knowledge.manual')}</option>
                  <option value="policy">{t('knowledge.policy')}</option>
                  <option value="other">{t('knowledge.other')}</option>
                </select>
              </div>
            </div>

            <div className="flex justify-end gap-2 mt-6">
              <button
                onClick={() => setEditingDoc(null)}
                className="px-4 py-2 border rounded hover:bg-gray-50"
              >
                {t('common.cancel')}
              </button>
              <button onClick={handleSaveDoc} className="btn-primary">
                {t('common.save')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Knowledge;
