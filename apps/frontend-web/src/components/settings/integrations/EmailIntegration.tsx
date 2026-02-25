import { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { Mail, Loader2, CheckCircle2, AlertCircle, Trash2, Send } from 'lucide-react';
import { Button } from '../../ui/button';
import { Label } from '../../ui/label';
import { apiRequest } from '../../../lib/api-client';
import type { AppSettings } from '../../../shared/types';

interface EmailAccount {
  id: string;
  provider: string;
  email_address: string;
  created_at: string | null;
}

interface CredentialsStatus {
  microsoft: boolean;
}

interface EmailIntegrationProps {
  settings: AppSettings;
  onSettingsChange: (settings: AppSettings) => void;
}

/**
 * Email integration component for connecting OAuth email accounts.
 * Displayed within the Notifications section when email is enabled.
 */
export function EmailIntegration({ settings: _settings, onSettingsChange: _onSettingsChange }: EmailIntegrationProps) {
  const { t } = useTranslation('settings');
  const [accounts, setAccounts] = useState<EmailAccount[]>([]);
  const [credentialsStatus, setCredentialsStatus] = useState<CredentialsStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isConnecting, setIsConnecting] = useState(false);
  const [testingAccountId, setTestingAccountId] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const loadAccounts = useCallback(async () => {
    const result = await apiRequest<EmailAccount[]>('/email/accounts');
    if (result.success && result.data) {
      setAccounts(result.data);
    }
  }, []);

  const loadCredentialsStatus = useCallback(async () => {
    const result = await apiRequest<CredentialsStatus>('/email/credentials-status');
    if (result.success && result.data) {
      setCredentialsStatus(result.data);
    }
  }, []);

  useEffect(() => {
    Promise.all([loadAccounts(), loadCredentialsStatus()]).finally(() => setIsLoading(false));
  }, [loadAccounts, loadCredentialsStatus]);

  // Listen for OAuth callback messages from popup
  useEffect(() => {
    const handleMessage = (event: MessageEvent) => {
      if (event.data?.type === 'email-oauth-callback') {
        setIsConnecting(false);
        if (event.data.status === 'success') {
          setStatusMessage({ type: 'success', text: t('email.connectionSuccess') });
          loadAccounts();
        } else {
          setStatusMessage({ type: 'error', text: event.data.message || t('email.connectionFailed') });
        }
        // Clear status after 5 seconds
        setTimeout(() => setStatusMessage(null), 5000);
      }
    };

    window.addEventListener('message', handleMessage);
    return () => window.removeEventListener('message', handleMessage);
  }, [loadAccounts, t]);

  const handleConnectOutlook = async () => {
    setIsConnecting(true);
    setStatusMessage(null);

    const result = await apiRequest<{ authUrl: string }>('/email/auth/outlook/start');
    if (result.success && result.data?.authUrl) {
      // Open OAuth popup
      const width = 600;
      const height = 700;
      const left = window.screenX + (window.innerWidth - width) / 2;
      const top = window.screenY + (window.innerHeight - height) / 2;
      window.open(
        result.data.authUrl,
        'email-oauth',
        `width=${width},height=${height},left=${left},top=${top},popup=yes`
      );
    } else {
      setIsConnecting(false);
      setStatusMessage({ type: 'error', text: result.error || t('email.connectionFailed') });
      setTimeout(() => setStatusMessage(null), 5000);
    }
  };

  const handleDisconnect = async (accountId: string) => {
    const result = await apiRequest(`/email/accounts/${accountId}`, { method: 'DELETE' });
    if (result.success) {
      setAccounts(prev => prev.filter(a => a.id !== accountId));
    }
  };

  const handleTestEmail = async (accountId: string) => {
    setTestingAccountId(accountId);
    const result = await apiRequest(`/email/test/${accountId}`, { method: 'POST' });
    setTestingAccountId(null);
    if (result.success) {
      setStatusMessage({ type: 'success', text: t('email.testEmailSent') });
    } else {
      setStatusMessage({ type: 'error', text: result.error || t('email.connectionFailed') });
    }
    setTimeout(() => setStatusMessage(null), 5000);
  };

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 p-4 text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" />
        {t('email.loading')}
      </div>
    );
  }

  const outlookAccount = accounts.find(a => a.provider === 'outlook');
  const canConnectOutlook = credentialsStatus?.microsoft && !outlookAccount;

  return (
    <div className="space-y-3 p-4 rounded-lg border border-border bg-muted/30">
      <div className="flex items-center gap-2">
        <Mail className="h-4 w-4 text-muted-foreground" />
        <Label className="font-medium text-foreground">{t('email.title')}</Label>
      </div>
      <p className="text-sm text-muted-foreground">{t('email.description')}</p>

      {/* Status message */}
      {statusMessage && (
        <div className={`flex items-center gap-2 p-3 rounded-md text-sm ${
          statusMessage.type === 'success'
            ? 'bg-green-500/10 text-green-600 dark:text-green-400'
            : 'bg-red-500/10 text-red-600 dark:text-red-400'
        }`}>
          {statusMessage.type === 'success' ? (
            <CheckCircle2 className="h-4 w-4 shrink-0" />
          ) : (
            <AlertCircle className="h-4 w-4 shrink-0" />
          )}
          {statusMessage.text}
        </div>
      )}

      {/* Connected Outlook account */}
      {outlookAccount && (
        <div className="flex items-center justify-between p-3 rounded-md border border-border bg-background">
          <div className="flex items-center gap-3">
            <div className="flex items-center justify-center w-8 h-8 rounded bg-blue-500/10">
              <Mail className="h-4 w-4 text-blue-500" />
            </div>
            <div>
              <p className="text-sm font-medium">{outlookAccount.email_address}</p>
              <p className="text-xs text-muted-foreground">{t('email.connectedVia')} Outlook</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => handleTestEmail(outlookAccount.id)}
              disabled={testingAccountId === outlookAccount.id}
            >
              {testingAccountId === outlookAccount.id ? (
                <Loader2 className="h-3 w-3 animate-spin mr-1" />
              ) : (
                <Send className="h-3 w-3 mr-1" />
              )}
              {t('email.sendTestEmail')}
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => handleDisconnect(outlookAccount.id)}
              className="text-destructive hover:text-destructive"
            >
              <Trash2 className="h-3 w-3 mr-1" />
              {t('email.disconnect')}
            </Button>
          </div>
        </div>
      )}

      {/* Connect button */}
      {canConnectOutlook && (
        <Button
          variant="outline"
          size="sm"
          onClick={handleConnectOutlook}
          disabled={isConnecting}
        >
          {isConnecting ? (
            <Loader2 className="h-4 w-4 animate-spin mr-2" />
          ) : (
            <Mail className="h-4 w-4 mr-2" />
          )}
          {t('email.connectOutlook')}
        </Button>
      )}

      {/* No credentials configured */}
      {!credentialsStatus?.microsoft && !outlookAccount && (
        <div className="flex items-center gap-2 p-3 rounded-md bg-muted/50 text-sm text-muted-foreground">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{t('email.noCredentialsConfigured')}</span>
        </div>
      )}
    </div>
  );
}
