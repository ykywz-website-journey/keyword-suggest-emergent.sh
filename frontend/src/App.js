import React, { useState, useEffect } from "react";
import "./App.css";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const KeywordSuggestionApp = () => {
  const [query, setQuery] = useState("");
  const [selectedSource, setSelectedSource] = useState("google");
  const [suggestions, setSuggestions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [savedKeywords, setSavedKeywords] = useState([]);
  const [searchHistory, setSearchHistory] = useState([]);
  const [bulkSearchMode, setBulkSearchMode] = useState(false);
  const [bulkProgress, setBulkProgress] = useState({ current: 0, total: 0 });

  // Load saved keywords and search history from localStorage on component mount
  useEffect(() => {
    const saved = localStorage.getItem("savedKeywords");
    const history = localStorage.getItem("searchHistory");
    
    if (saved) {
      setSavedKeywords(JSON.parse(saved));
    }
    if (history) {
      setSearchHistory(JSON.parse(history));
    }
  }, []);

  // Save to localStorage whenever savedKeywords changes
  useEffect(() => {
    localStorage.setItem("savedKeywords", JSON.stringify(savedKeywords));
  }, [savedKeywords]);

  // Save to localStorage whenever searchHistory changes
  useEffect(() => {
    localStorage.setItem("searchHistory", JSON.stringify(searchHistory));
  }, [searchHistory]);

  const fetchSuggestions = async () => {
    if (!query.trim()) return;
    
    setLoading(true);
    setBulkSearchMode(false);
    try {
      const response = await axios.get(`${API}/suggestions/${selectedSource}`, {
        params: { q: query }
      });
      
      setSuggestions(response.data.suggestions || []);
      
      // Add to search history
      const newHistoryItem = {
        query,
        source: selectedSource,
        timestamp: new Date().toISOString()
      };
      
      setSearchHistory(prev => {
        const filtered = prev.filter(item => !(item.query === query && item.source === selectedSource));
        return [newHistoryItem, ...filtered].slice(0, 10); // Keep only last 10 searches
      });
      
    } catch (error) {
      console.error("Error fetching suggestions:", error);
      setSuggestions([]);
    } finally {
      setLoading(false);
    }
  };

  const fetchBulkSuggestions = async () => {
    if (!query.trim()) return;
    
    setLoading(true);
    setBulkSearchMode(true);
    setSuggestions([]);
    
    // Generate all variations: a-z and 0-9
    const suffixes = [];
    
    // Add a-z
    for (let i = 97; i <= 122; i++) {
      suffixes.push(String.fromCharCode(i));
    }
    
    // Add 0-9
    for (let i = 0; i <= 9; i++) {
      suffixes.push(i.toString());
    }
    
    setBulkProgress({ current: 0, total: suffixes.length });
    
    const allSuggestions = [];
    const batchSize = 5; // Process 5 requests at a time to avoid overwhelming the server
    
    try {
      for (let i = 0; i < suffixes.length; i += batchSize) {
        const batch = suffixes.slice(i, i + batchSize);
        
        // Create batch of requests
        const batchPromises = batch.map(async (suffix) => {
          try {
            const searchQuery = query + suffix;
            const response = await axios.get(`${API}/suggestions/${selectedSource}`, {
              params: { q: searchQuery }
            });
            
            return {
              query: searchQuery,
              suggestions: response.data.suggestions || [],
              source: selectedSource
            };
          } catch (error) {
            console.error(`Error fetching suggestions for ${query}${suffix}:`, error);
            return { query: query + suffix, suggestions: [], source: selectedSource };
          }
        });
        
        // Wait for batch to complete
        const batchResults = await Promise.all(batchPromises);
        
        // Add suggestions to the list
        batchResults.forEach(result => {
          result.suggestions.forEach(suggestion => {
            // Avoid duplicates
            if (!allSuggestions.find(s => s.text === suggestion && s.source === result.source)) {
              allSuggestions.push({
                text: suggestion,
                source: result.source,
                originalQuery: result.query
              });
            }
          });
        });
        
        // Update progress
        setBulkProgress({ current: Math.min(i + batchSize, suffixes.length), total: suffixes.length });
        
        // Add a small delay between batches to be respectful to the APIs
        if (i + batchSize < suffixes.length) {
          await new Promise(resolve => setTimeout(resolve, 500));
        }
      }
      
      setSuggestions(allSuggestions);
      
      // Add to search history
      const newHistoryItem = {
        query: `${query} (bulk a-z, 0-9)`,
        source: selectedSource,
        timestamp: new Date().toISOString()
      };
      
      setSearchHistory(prev => {
        const filtered = prev.filter(item => !(item.query.includes(query) && item.source === selectedSource));
        return [newHistoryItem, ...filtered].slice(0, 10);
      });
      
    } catch (error) {
      console.error("Error during bulk fetch:", error);
    } finally {
      setLoading(false);
      setBulkSearchMode(false);
      setBulkProgress({ current: 0, total: 0 });
    }
  };

  const fetchAllSuggestions = async () => {
    if (!query.trim()) return;
    
    setLoading(true);
    try {
      const response = await axios.get(`${API}/suggestions/all`, {
        params: { q: query }
      });
      
      // Combine all suggestions from different sources
      const allSuggestions = [];
      response.data.forEach(sourceData => {
        sourceData.suggestions.forEach(suggestion => {
          allSuggestions.push({
            text: suggestion,
            source: sourceData.source
          });
        });
      });
      
      setSuggestions(allSuggestions);
      
      // Add to search history
      const newHistoryItem = {
        query,
        source: "all",
        timestamp: new Date().toISOString()
      };
      
      setSearchHistory(prev => {
        const filtered = prev.filter(item => !(item.query === query && item.source === "all"));
        return [newHistoryItem, ...filtered].slice(0, 10);
      });
      
    } catch (error) {
      console.error("Error fetching all suggestions:", error);
      setSuggestions([]);
    } finally {
      setLoading(false);
    }
  };

  const saveKeyword = (keyword, source = selectedSource) => {
    const newKeyword = {
      id: Date.now() + Math.random(), // Ensure unique IDs
      text: keyword,
      source: source,
      savedAt: new Date().toISOString()
    };
    
    // Check if already saved
    const exists = savedKeywords.find(k => k.text === keyword && k.source === source);
    if (!exists) {
      setSavedKeywords(prev => [newKeyword, ...prev]);
    }
  };

  const saveAllSuggestions = () => {
    const newKeywords = [];
    
    suggestions.forEach(suggestion => {
      const text = typeof suggestion === "string" ? suggestion : suggestion.text;
      const source = typeof suggestion === "string" ? selectedSource : suggestion.source;
      
      // Check if not already saved
      const exists = savedKeywords.find(k => k.text === text && k.source === source);
      if (!exists && !newKeywords.find(k => k.text === text && k.source === source)) {
        newKeywords.push({
          id: Date.now() + Math.random() + newKeywords.length,
          text: text,
          source: source,
          savedAt: new Date().toISOString()
        });
      }
    });
    
    if (newKeywords.length > 0) {
      setSavedKeywords(prev => [...newKeywords, ...prev]);
    }
  };

  const removeKeyword = (id) => {
    setSavedKeywords(prev => prev.filter(k => k.id !== id));
  };

  const clearAllSaved = () => {
    setSavedKeywords([]);
  };

  const exportKeywords = () => {
    const dataStr = JSON.stringify(savedKeywords, null, 2);
    const dataBlob = new Blob([dataStr], { type: "application/json" });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "saved-keywords.json";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter") {
      if (selectedSource === "all") {
        fetchAllSuggestions();
      } else {
        fetchSuggestions();
      }
    }
  };

  const handleBulkKeyPress = (e) => {
    if (e.key === "Enter") {
      fetchBulkSuggestions();
    }
  };

  const getSourceIcon = (source) => {
    switch (source) {
      case "google": return "🔍";
      case "amazon": return "📦";
      case "youtube": return "🎥";
      case "all": return "🌐";
      default: return "💡";
    }
  };

  const getSourceColor = (source) => {
    switch (source) {
      case "google": return "bg-blue-100 text-blue-800";
      case "amazon": return "bg-orange-100 text-orange-800";
      case "youtube": return "bg-red-100 text-red-800";
      case "all": return "bg-purple-100 text-purple-800";
      default: return "bg-gray-100 text-gray-800";
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-800 mb-2">
            🔍 Keyword Suggestion Tool
          </h1>
          <p className="text-gray-600">
            Get keyword suggestions from Google, Amazon, and YouTube
          </p>
        </div>

        {/* Search Section */}
        <div className="bg-white rounded-xl shadow-lg p-6 mb-8">
          <div className="flex flex-col space-y-4">
            {/* Source Selection */}
            <div className="flex flex-wrap gap-2">
              <label className="text-sm font-medium text-gray-700 mr-4">Source:</label>
              {["google", "amazon", "youtube", "all"].map((source) => (
                <button
                  key={source}
                  onClick={() => setSelectedSource(source)}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                    selectedSource === source
                      ? "bg-indigo-600 text-white shadow-md"
                      : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                  }`}
                >
                  {getSourceIcon(source)} {source.charAt(0).toUpperCase() + source.slice(1)}
                </button>
              ))}
            </div>

            {/* Search Input */}
            <div className="flex space-x-4">
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Enter your keyword..."
                className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
              />
              <button
                onClick={selectedSource === "all" ? fetchAllSuggestions : fetchSuggestions}
                disabled={loading || !query.trim()}
                className="px-6 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {loading && !bulkSearchMode ? "Searching..." : "Search"}
              </button>
              <button
                onClick={fetchBulkSuggestions}
                disabled={loading || !query.trim() || selectedSource === "all"}
                className="px-6 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                title="Search with a-z and 0-9 variations"
              >
                {loading && bulkSearchMode ? "Bulk Search..." : "🔤 Bulk A-Z"}
              </button>
            </div>
            
            {/* Bulk Search Progress */}
            {bulkSearchMode && (
              <div className="mt-4 p-4 bg-purple-50 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-purple-700">
                    Searching variations... ({bulkProgress.current}/{bulkProgress.total})
                  </span>
                  <span className="text-sm text-purple-600">
                    {Math.round((bulkProgress.current / bulkProgress.total) * 100)}%
                  </span>
                </div>
                <div className="w-full bg-purple-200 rounded-full h-2">
                  <div 
                    className="bg-purple-600 h-2 rounded-full transition-all duration-300"
                    style={{ width: `${(bulkProgress.current / bulkProgress.total) * 100}%` }}
                  ></div>
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Suggestions Section */}
          <div className="bg-white rounded-xl shadow-lg p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-2xl font-semibold text-gray-800">
                Suggestions {query && `for "${query}"`} ({suggestions.length})
              </h2>
              {suggestions.length > 0 && (
                <button
                  onClick={saveAllSuggestions}
                  className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors text-sm"
                >
                  💾 Save All ({suggestions.length})
                </button>
              )}
            </div>
            
            {loading ? (
              <div className="flex items-center justify-center py-8">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
                <span className="ml-2 text-gray-600">
                  {bulkSearchMode ? 
                    `Loading bulk suggestions... (${bulkProgress.current}/${bulkProgress.total})` : 
                    "Loading suggestions..."
                  }
                </span>
              </div>
            ) : suggestions.length > 0 ? (
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {suggestions.map((suggestion, index) => {
                  const text = typeof suggestion === "string" ? suggestion : suggestion.text;
                  const source = typeof suggestion === "string" ? selectedSource : suggestion.source;
                  const originalQuery = typeof suggestion === "object" ? suggestion.originalQuery : undefined;
                  
                  return (
                    <div
                      key={`${text}-${index}`}
                      className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                    >
                      <div className="flex items-center space-x-3 flex-1">
                        <span className={`px-2 py-1 text-xs rounded-full ${getSourceColor(source)}`}>
                          {getSourceIcon(source)} {source}
                        </span>
                        <div className="flex-1">
                          <span className="text-gray-800">{text}</span>
                          {originalQuery && (
                            <div className="text-xs text-gray-500 mt-1">
                              from: {originalQuery}
                            </div>
                          )}
                        </div>
                      </div>
                      <button
                        onClick={() => saveKeyword(text, source)}
                        className="px-3 py-1 bg-green-500 text-white text-sm rounded hover:bg-green-600 transition-colors ml-2 flex-shrink-0"
                      >
                        Save
                      </button>
                    </div>
                  );
                })}
              </div>
            ) : query ? (
              <p className="text-gray-500 text-center py-8">No suggestions found. Try a different keyword.</p>
            ) : (
              <div className="text-gray-500 text-center py-8">
                <p className="mb-4">Enter a keyword to get suggestions.</p>
                <div className="text-sm space-y-2">
                  <p><strong>💡 Pro Tips:</strong></p>
                  <p>• Use <strong>🔤 Bulk A-Z</strong> to search "keyword" + a,b,c...z,0,1,2...9</p>
                  <p>• Perfect for finding long-tail keyword variations</p>
                  <p>• Use <strong>💾 Save All</strong> to quickly save all results</p>
                </div>
              </div>
            )}
          </div>

          {/* Saved Keywords Section */}
          <div className="bg-white rounded-xl shadow-lg p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-2xl font-semibold text-gray-800">
                Saved Keywords ({savedKeywords.length})
              </h2>
              <div className="space-x-2">
                <button
                  onClick={exportKeywords}
                  disabled={savedKeywords.length === 0}
                  className="px-3 py-2 bg-blue-500 text-white text-sm rounded hover:bg-blue-600 disabled:opacity-50 transition-colors"
                >
                  Export
                </button>
                <button
                  onClick={clearAllSaved}
                  disabled={savedKeywords.length === 0}
                  className="px-3 py-2 bg-red-500 text-white text-sm rounded hover:bg-red-600 disabled:opacity-50 transition-colors"
                >
                  Clear All
                </button>
              </div>
            </div>

            {savedKeywords.length > 0 ? (
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {savedKeywords.map((keyword) => (
                  <div
                    key={keyword.id}
                    className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                  >
                    <div className="flex items-center space-x-3">
                      <span className={`px-2 py-1 text-xs rounded-full ${getSourceColor(keyword.source)}`}>
                        {getSourceIcon(keyword.source)} {keyword.source}
                      </span>
                      <span className="text-gray-800">{keyword.text}</span>
                    </div>
                    <button
                      onClick={() => removeKeyword(keyword.id)}
                      className="px-3 py-1 bg-red-500 text-white text-sm rounded hover:bg-red-600 transition-colors"
                    >
                      Remove
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-gray-500 text-center py-8">No saved keywords yet.</p>
            )}
          </div>
        </div>

        {/* Search History */}
        {searchHistory.length > 0 && (
          <div className="mt-8 bg-white rounded-xl shadow-lg p-6">
            <h2 className="text-2xl font-semibold text-gray-800 mb-4">Recent Searches</h2>
            <div className="flex flex-wrap gap-2">
              {searchHistory.map((item, index) => (
                <button
                  key={index}
                  onClick={() => {
                    setQuery(item.query);
                    setSelectedSource(item.source);
                  }}
                  className="px-3 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors text-sm"
                >
                  {getSourceIcon(item.source)} {item.query}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

function App() {
  return (
    <div className="App">
      <KeywordSuggestionApp />
    </div>
  );
}

export default App;