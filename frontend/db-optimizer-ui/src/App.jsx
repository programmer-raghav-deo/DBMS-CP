import React, { useState } from 'react';

export default function App() {
  const [dbType, setDbType] = useState('mysql');
  const [mysqlUri, setMysqlUri] = useState('');
  const [file, setFile] = useState(null);
  
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setResults(null);

    const formData = new FormData();
    let endpoint = 'http://localhost:8000/api/optimize/mysql';

    if (dbType === 'mysql') {
      if (!mysqlUri) {
        setError('Please enter a MySQL URI');
        setLoading(false);
        return;
      }
      formData.append('mysql_uri', mysqlUri);
    } else {
      if (!file) {
        setError('Please upload a .db file');
        setLoading(false);
        return;
      }
      formData.append('file', file);
      endpoint = 'http://localhost:8000/api/optimize/sqlite';
    }

    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();
      
      if (!response.ok || data.error) {
        throw new Error(data.detail || data.error || 'Optimization failed');
      }

      setResults(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen p-8 font-sans text-slate-800">
      <div className="max-w-4xl mx-auto">
        
        {/* Header */}
        <div className="flex items-center gap-3 mb-8">
          <span className="text-3xl">📊</span>
          <h1 className="text-3xl font-bold">Agentic DB Optimizer</h1>
        </div>

        {/* Input Panel */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 mb-8">
          <div className="flex gap-4 mb-6">
            <button
              onClick={() => setDbType('mysql')}
              className={`flex-1 py-3 px-4 rounded-lg flex items-center justify-center gap-2 font-medium transition-colors ${
                dbType === 'mysql' ? 'bg-blue-50 text-blue-700 border-2 border-blue-500' : 'bg-slate-50 text-slate-600 border-2 border-transparent'
              }`}
            >
              🗄️ MySQL Connection
            </button>
            <button
              onClick={() => setDbType('sqlite')}
              className={`flex-1 py-3 px-4 rounded-lg flex items-center justify-center gap-2 font-medium transition-colors ${
                dbType === 'sqlite' ? 'bg-blue-50 text-blue-700 border-2 border-blue-500' : 'bg-slate-50 text-slate-600 border-2 border-transparent'
              }`}
            >
              💾 SQLite Upload
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {dbType === 'mysql' ? (
              <div>
                <label className="block text-sm font-medium mb-1">MySQL Connection URI</label>
                <input
                  type="text"
                  placeholder="mysql+pymysql://user:password@localhost:3306/dbname"
                  className="w-full p-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                  value={mysqlUri}
                  onChange={(e) => setMysqlUri(e.target.value)}
                />
              </div>
            ) : (
              <div>
                <label className="block text-sm font-medium mb-1">Upload .db File</label>
                <div className="border-2 border-dashed border-slate-300 rounded-lg p-8 text-center hover:bg-slate-50 transition-colors">
                  <div className="text-3xl mb-2">📤</div>
                  <input
                    type="file"
                    accept=".db,.sqlite"
                    className="w-full max-w-xs mx-auto block text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
                    onChange={(e) => setFile(e.target.files[0])}
                  />
                </div>
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 rounded-lg flex justify-center items-center gap-2 transition-colors disabled:opacity-50"
            >
              {loading ? 'Agents are analyzing...' : 'Run Optimization Pipeline'}
            </button>
          </form>

          {error && (
            <div className="mt-4 p-4 bg-red-50 text-red-700 rounded-lg flex items-center gap-2">
              <span>⚠️</span> {error}
            </div>
          )}
        </div>

        {/* Results Panel */}
        {results && (
          <div className="space-y-6">
            <h2 className="text-2xl font-bold flex items-center gap-2">
              <span className="text-green-500">✅</span> Optimization Complete
            </h2>

            <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
              <div className="bg-slate-50 p-4 border-b border-slate-200">
                <h3 className="font-bold text-lg text-slate-800">Agent 1: Schema Analysis</h3>
              </div>
              <div className="p-4 whitespace-pre-wrap text-sm font-mono text-slate-600">
                {results.agent_1_report}
              </div>
            </div>

            <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
              <div className="bg-slate-50 p-4 border-b border-slate-200">
                <h3 className="font-bold text-lg text-slate-800">Agent 2: Hash Logic Generation</h3>
              </div>
              <div className="p-4 whitespace-pre-wrap text-sm font-mono text-slate-600">
                {results.agent_2_hash_logic}
              </div>
            </div>

            <div className="bg-white rounded-xl shadow-sm border border-slate-200 border-l-4 border-l-green-500 overflow-hidden">
              <div className="bg-slate-50 p-4 border-b border-slate-200">
                <h3 className="font-bold text-lg text-slate-800">Agent 3: SQL Execution Status</h3>
              </div>
              <div className="p-4 whitespace-pre-wrap text-sm font-mono text-slate-600">
                {results.agent_3_execution_status}
              </div>
            </div>
            
          </div>
        )}
      </div>
    </div>
  );
}