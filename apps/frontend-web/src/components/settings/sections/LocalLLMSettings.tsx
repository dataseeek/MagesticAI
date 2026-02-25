import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Server } from 'lucide-react';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { apiRequest } from '@/lib/api-client';
import type { AppSettings } from '@/shared/types/settings';

interface LocalLLMSettingsProps {
  settings: AppSettings;
  onSettingsChange: (settings: AppSettings) => void;
}

export function LocalLLMSettings({ settings, onSettingsChange }: LocalLLMSettingsProps) {
  const { t } = useTranslation(['settings', 'common']);
  const [ollamaModels, setOllamaModels] = useState<any[]>([]);
  const [isTestingConnection, setIsTestingConnection] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<{type: 'success'|'error', message: string} | null>(null);

  useEffect(() => {
    fetchOllamaModels();
  }, [settings.llmOllamaBaseUrl]);

  const fetchOllamaModels = async () => {
    try {
      const result = await apiRequest<{ models: any[] }>(
        `/settings/ollama/models?ollamaBaseUrl=${encodeURIComponent(settings.llmOllamaBaseUrl || 'http://localhost:11434')}`
      );
      if (result.success && result.data) {
        setOllamaModels(result.data.models);
      }
    } catch (error) {
      console.error('Failed to fetch Ollama models:', error);
    }
  };

  const testConnection = async () => {
    setIsTestingConnection(true);
    setConnectionStatus(null);
    try {
      const result = await apiRequest<{ message: string }>('/settings/ollama/test', {
        method: 'POST',
        body: {
          ollamaBaseUrl: settings.llmOllamaBaseUrl || 'http://localhost:11434',
          modelName: settings.llmOllamaModel || 'qwen3-30b-local:latest'
        }
      });
      setConnectionStatus({
        type: result.success ? 'success' : 'error',
        message: result.success
          ? ((result.data as any)?.message || (result as any).message || 'Connected!')
          : (result.error || 'Connection failed')
      });
    } catch (error) {
      setConnectionStatus({ type: 'error', message: String(error) });
    } finally {
      setIsTestingConnection(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <Server className="h-4 w-4 text-muted-foreground" />
        <h4 className="text-sm font-semibold text-foreground">{t('settings:sections.llmProvider.localLlms.title')}</h4>
      </div>
      <p className="text-sm text-muted-foreground">
        {t('settings:sections.llmProvider.localLlms.description')}
      </p>

      <div className="space-y-2">
        <Label>{t('settings:sections.llmProvider.ollama.baseUrl')}</Label>
        <Input
          value={settings.llmOllamaBaseUrl || 'http://localhost:11434'}
          onChange={(e) => onSettingsChange({ ...settings, llmOllamaBaseUrl: e.target.value })}
          placeholder="http://localhost:11434"
          className="max-w-md"
        />
      </div>

      <div className="space-y-2">
        <Label>{t('settings:sections.llmProvider.ollama.model')}</Label>
        <Select
          value={settings.llmOllamaModel || 'qwen3-30b-local:latest'}
          onValueChange={(value) => onSettingsChange({ ...settings, llmOllamaModel: value })}
        >
          <SelectTrigger className="w-full max-w-md">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {ollamaModels.length > 0 ? (
              ollamaModels.map((model) => (
                <SelectItem key={model.name} value={model.name}>
                  {model.name} ({(model.size / 1e9).toFixed(1)} GB)
                </SelectItem>
              ))
            ) : (
              <SelectItem value={settings.llmOllamaModel || 'qwen3-30b-local:latest'}>
                {settings.llmOllamaModel || 'qwen3-30b-local:latest'}
              </SelectItem>
            )}
          </SelectContent>
        </Select>
        <Button size="sm" variant="outline" onClick={fetchOllamaModels}>
          {t('settings:sections.llmProvider.ollama.refreshModels')}
        </Button>
      </div>

      <div className="flex items-center gap-2">
        <Button onClick={testConnection} disabled={isTestingConnection} size="sm">
          {isTestingConnection ? t('common:testing') : t('settings:sections.llmProvider.testConnection')}
        </Button>
        {connectionStatus && (
          <Badge variant={connectionStatus.type === 'success' ? 'success' : 'destructive'}>
            {connectionStatus.message}
          </Badge>
        )}
      </div>
    </div>
  );
}
