import { useState, useEffect, useCallback, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import {
  FileText,
  FileJson,
  FileCode,
  Loader2,
  AlertCircle,
  FolderOpen,
  RefreshCw,
  ChevronRight,
  ExternalLink,
  Download
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import { ScrollArea } from '../ui/scroll-area';
import { Button } from '../ui/button';
import { Tooltip, TooltipContent, TooltipTrigger } from '../ui/tooltip';
import { cn } from '../../lib/utils';
import { useSettingsStore } from '../../stores/settings-store';
import { CodeBlock } from '../ui/code-block';
import { detectLanguage } from '../../lib/highlight-config';
import type { Task } from '../../shared/types';
import type { FileNode } from '../../shared/types/project';

interface TaskFilesProps {
  task: Task;
}

// File extensions to display
const ALLOWED_EXTENSIONS = [
  '.md', '.json',
  '.js', '.jsx', '.ts', '.tsx',
  '.py', '.yaml', '.yml', '.sh', '.bash',
  '.go', '.rs', '.java', '.rb', '.php',
  '.c', '.cpp', '.h', '.hpp', '.cs',
  '.html', '.css', '.scss', '.sass',
  '.sql', '.xml', '.toml', '.ini', '.txt'
];

// Get icon for file type
function getFileIcon(filename: string) {
  const ext = filename.split('.').pop()?.toLowerCase();

  if (ext === 'json') {
    return <FileJson className="h-4 w-4 text-amber-500" />;
  }

  // Code files
  if (['js', 'jsx', 'ts', 'tsx', 'py', 'sh', 'bash', 'go', 'rs', 'java', 'rb', 'php', 'c', 'cpp', 'cs', 'html', 'css', 'scss'].includes(ext || '')) {
    return <FileCode className="h-4 w-4 text-blue-500" />;
  }

  // Markdown and text
  if (ext === 'md' || ext === 'txt') {
    return <FileText className="h-4 w-4 text-green-500" />;
  }

  return <FileText className="h-4 w-4 text-muted-foreground" />;
}

export function TaskFiles({ task }: TaskFilesProps) {
  const { t } = useTranslation(['tasks']);
  const { settings } = useSettingsStore();

  // State for file listing
  const [files, setFiles] = useState<FileNode[]>([]);
  const [isLoadingFiles, setIsLoadingFiles] = useState(false);
  const [filesError, setFilesError] = useState<string | null>(null);

  // State for file content
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [fileContent, setFileContent] = useState<string | null>(null);
  const [isLoadingContent, setIsLoadingContent] = useState(false);
  const [contentError, setContentError] = useState<string | null>(null);

  // Ref for keyboard navigation
  const fileListRef = useRef<HTMLDivElement>(null);

  // Load files from spec directory
  const loadFiles = useCallback(async () => {
    if (!task.specsPath) return;

    setIsLoadingFiles(true);
    setFilesError(null);

    try {
      const result = await window.API.listDirectory(task.specsPath);
      if (!result.success || !result.data) {
        throw new Error(result.error || 'Failed to load directory');
      }

      // Extract entries array from response (web API returns {path, entries, parent})
      const entries = Array.isArray(result.data) ? result.data : result.data.entries || [];

      // Filter to only show allowed file types
      const filteredFiles = entries.filter(
        (file) => file.type !== 'directory' && ALLOWED_EXTENSIONS.some(ext => file.name.endsWith(ext))
      );

      // Sort files: spec.md first, then alphabetically
      filteredFiles.sort((a, b) => {
        if (a.name === 'spec.md') return -1;
        if (b.name === 'spec.md') return 1;
        return a.name.localeCompare(b.name);
      });

      setFiles(filteredFiles);
    } catch (err) {
      setFilesError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setIsLoadingFiles(false);
    }
  }, [task.specsPath]);

  // Load file content
  const loadFileContent = useCallback(async (filePath: string) => {
    setSelectedFile(filePath);
    setIsLoadingContent(true);
    setContentError(null);
    setFileContent(null);

    try {
      const result = await window.API.readFile(filePath);
      if (!result.success || !result.data) {
        throw new Error(result.error || 'Failed to read file');
      }
      setFileContent(result.data.content);
    } catch (err) {
      setContentError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setIsLoadingContent(false);
    }
  }, []);

  // Reset state when task.specsPath changes
  useEffect(() => {
    setSelectedFile(null);
    setFileContent(null);
    setContentError(null);
  }, [task.specsPath]);

  // Load files on mount and when specsPath changes
  useEffect(() => {
    loadFiles();
  }, [loadFiles]);

  // Auto-select first file (spec.md) when files are loaded
  useEffect(() => {
    if (files.length > 0 && selectedFile === null) {
      loadFileContent(files[0].path);
    }
    // Only run when files change, not on selectedFile changes
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [files]);

  // Open spec directory in IDE
  const handleOpenInIDE = useCallback(async () => {
    if (!settings.preferredIDE || !task.specsPath) return;

    try {
      await window.API.worktreeOpenInIDE(
        task.specsPath,
        settings.preferredIDE,
        settings.customIDEPath
      );
    } catch (err) {
      console.error('Failed to open in IDE:', err);
    }
  }, [settings.preferredIDE, settings.customIDEPath, task.specsPath]);

  // Download current file
  const handleDownloadFile = useCallback(() => {
    if (!selectedFile || fileContent === null) return;

    const fileName = selectedFile.split(/[/\\]/).pop() || 'file';
    const blob = new Blob([fileContent], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = fileName;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, [selectedFile, fileContent]);

  // Keyboard navigation for file list
  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (files.length === 0) return;

    const currentIndex = selectedFile
      ? files.findIndex(f => f.path === selectedFile)
      : -1;

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        if (currentIndex < files.length - 1) {
          loadFileContent(files[currentIndex + 1].path);
        }
        break;
      case 'ArrowUp':
        e.preventDefault();
        if (currentIndex > 0) {
          loadFileContent(files[currentIndex - 1].path);
        }
        break;
      case 'Home':
        e.preventDefault();
        loadFileContent(files[0].path);
        break;
      case 'End':
        e.preventDefault();
        loadFileContent(files[files.length - 1].path);
        break;
    }
  }, [files, selectedFile, loadFileContent]);

  // Handle no specsPath
  if (!task.specsPath) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center py-12">
          <FolderOpen className="h-10 w-10 mx-auto mb-3 text-muted-foreground/30" />
          <p className="text-sm font-medium text-muted-foreground mb-1">
            {t('tasks:files.noSpecPath')}
          </p>
        </div>
      </div>
    );
  }

  // Render file content based on type
  const renderContent = () => {
    if (!selectedFile) {
      return (
        <div className="h-full flex items-center justify-center text-muted-foreground">
          <div className="text-center">
            <FileText className="h-8 w-8 mx-auto mb-2 opacity-50" />
            <p className="text-sm">{t('tasks:files.selectFile')}</p>
          </div>
        </div>
      );
    }

    if (isLoadingContent) {
      return (
        <div className="h-full flex items-center justify-center">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      );
    }

    if (contentError) {
      return (
        <div className="h-full flex items-center justify-center">
          <div className="text-center">
            <AlertCircle className="h-8 w-8 mx-auto mb-2 text-destructive" />
            <p className="text-sm text-destructive mb-2">{t('tasks:files.errorLoadingContent')}</p>
            <Button
              variant="outline"
              size="sm"
              onClick={() => loadFileContent(selectedFile)}
            >
              <RefreshCw className="h-3 w-3 mr-1" />
              {t('tasks:files.retry')}
            </Button>
          </div>
        </div>
      );
    }

    if (fileContent === null) return null;

    const fileName = selectedFile.split(/[/\\]/).pop() || '';

    // Markdown files: render with react-markdown + syntax highlighting for code blocks
    if (selectedFile.endsWith('.md')) {
      return (
        <div className="p-4 prose dark:prose-invert max-w-none">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            rehypePlugins={[rehypeHighlight]}
          >
            {fileContent}
          </ReactMarkdown>
        </div>
      );
    }

    // JSON files: format and highlight
    if (selectedFile.endsWith('.json')) {
      try {
        const formatted = JSON.stringify(JSON.parse(fileContent), null, 2);
        return (
          <CodeBlock
            code={formatted}
            language="json"
            fileName={fileName}
            showLineNumbers={true}
          />
        );
      } catch {
        // Invalid JSON - show raw with highlighting attempt
        return (
          <CodeBlock
            code={fileContent}
            language="json"
            fileName={fileName}
            showLineNumbers={true}
          />
        );
      }
    }

    // Other code files: detect language and highlight
    const language = detectLanguage(fileName);
    return (
      <CodeBlock
        code={fileContent}
        language={language}
        fileName={fileName}
        showLineNumbers={true}
      />
    );
  };

  // Get selected filename (cross-platform: handles both / and \ separators)
  const selectedFileName = selectedFile ? selectedFile.split(/[/\\]/).pop() : null;

  return (
    <div className="h-full flex">
      {/* File list sidebar */}
      <div className="w-52 border-r border-border flex flex-col">
        {/* Sidebar header */}
        <div className="px-3 py-2 border-b border-border flex items-center justify-between">
          <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
            {t('tasks:files.title')}
          </span>
          <Button
            variant="ghost"
            size="icon"
            className="h-6 w-6"
            onClick={loadFiles}
            disabled={isLoadingFiles}
          >
            <RefreshCw className={cn("h-3 w-3", isLoadingFiles && "animate-spin")} />
          </Button>
        </div>
        <ScrollArea className="flex-1">
          <div
            ref={fileListRef}
            className="p-2 space-y-1"
            role="listbox"
            aria-label={t('tasks:files.title')}
            tabIndex={files.length > 0 ? 0 : -1}
            onKeyDown={handleKeyDown}
          >
            {isLoadingFiles ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
              </div>
            ) : filesError ? (
              <div className="text-center py-4">
                <AlertCircle className="h-5 w-5 mx-auto mb-2 text-destructive" />
                <p className="text-xs text-destructive mb-2">{t('tasks:files.errorLoading')}</p>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={loadFiles}
                  className="text-xs"
                >
                  <RefreshCw className="h-3 w-3 mr-1" />
                  {t('tasks:files.retry')}
                </Button>
              </div>
            ) : files.length === 0 ? (
              <div className="text-center py-8">
                <FolderOpen className="h-8 w-8 mx-auto mb-2 text-muted-foreground/30" />
                <p className="text-xs text-muted-foreground">{t('tasks:files.noFiles')}</p>
              </div>
            ) : (
              files.map((file) => (
                <button
                  type="button"
                  key={file.path}
                  role="option"
                  aria-selected={selectedFile === file.path}
                  onClick={() => loadFileContent(file.path)}
                  className={cn(
                    'w-full flex items-center gap-2 px-2 py-1.5 rounded-md text-left transition-colors',
                    'hover:bg-secondary/50 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-1',
                    selectedFile === file.path && 'bg-secondary'
                  )}
                >
                  {getFileIcon(file.name)}
                  <span className="text-xs font-medium truncate flex-1">
                    {file.name}
                  </span>
                  {selectedFile === file.path && (
                    <ChevronRight className="h-3 w-3 text-muted-foreground" />
                  )}
                </button>
              ))
            )}
          </div>
        </ScrollArea>
      </div>

      {/* File content area */}
      <div className="flex-1 min-w-0 flex flex-col">
        {/* Content header */}
        {selectedFileName && (
          <div className="px-4 py-2 border-b border-border flex items-center gap-2 shrink-0 bg-muted/30">
            {getFileIcon(selectedFileName)}
            <span className="text-sm font-medium flex-1">{selectedFileName}</span>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7"
                  onClick={handleDownloadFile}
                  disabled={!fileContent}
                >
                  <Download className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                {t('tasks:files.downloadFile')}
              </TooltipContent>
            </Tooltip>
            {settings.preferredIDE && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7"
                    onClick={handleOpenInIDE}
                  >
                    <ExternalLink className="h-4 w-4" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  {t('tasks:files.openInIDE')}
                </TooltipContent>
              </Tooltip>
            )}
          </div>
        )}
        <ScrollArea className="flex-1">
          {renderContent()}
        </ScrollArea>
      </div>
    </div>
  );
}
