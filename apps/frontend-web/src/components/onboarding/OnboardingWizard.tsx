import { useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { Wand2 } from 'lucide-react';
import {
  FullScreenDialog,
  FullScreenDialogContent,
  FullScreenDialogHeader,
  FullScreenDialogBody,
  FullScreenDialogTitle,
  FullScreenDialogDescription
} from '../ui/full-screen-dialog';
import { ScrollArea } from '../ui/scroll-area';
import { WizardProgress, WizardStep } from './WizardProgress';
import { WelcomeStep } from './WelcomeStep';
import { ImportCredentialsStep } from './ImportCredentialsStep';
import { ClaudeCodeStep } from './ClaudeCodeStep';
import { OAuthStep } from './OAuthStep';
import { CompletionStep } from './CompletionStep';
import { useSettingsStore } from '../../stores/settings-store';

interface OnboardingWizardProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onOpenTaskCreator?: () => void;
  onOpenSettings?: () => void;
}

// Wizard step identifiers
type WizardStepId = 'welcome' | 'import-credentials' | 'claude-code' | 'oauth' | 'completion';

// Step configuration with translation keys
const WIZARD_STEPS: { id: WizardStepId; labelKey: string }[] = [
  { id: 'welcome', labelKey: 'steps.welcome' },
  { id: 'import-credentials', labelKey: 'steps.importCredentials' },
  { id: 'claude-code', labelKey: 'steps.claudeCode' },
  { id: 'oauth', labelKey: 'steps.auth' },
  { id: 'completion', labelKey: 'steps.done' }
];

/**
 * Main onboarding wizard component.
 * Provides a full-screen, multi-step wizard experience for new users
 * to connect their Claude account.
 *
 * Simplified flow:
 * 1. Welcome — Brief intro to MagesticAI
 * 2. Import Credentials (conditional) — Auto-import from ~/.claude/.credentials.json
 * 3. OAuth — Manual token setup
 * 4. Completion — Done
 */
export function OnboardingWizard({
  open,
  onOpenChange,
  onOpenTaskCreator,
  onOpenSettings
}: OnboardingWizardProps) {
  const { t } = useTranslation('onboarding');
  const { updateSettings } = useSettingsStore();
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [completedSteps, setCompletedSteps] = useState<Set<WizardStepId>>(new Set());

  // Get current step ID
  const currentStepId = WIZARD_STEPS[currentStepIndex].id;

  // Build step data for progress indicator
  const steps: WizardStep[] = WIZARD_STEPS.map((step, index) => ({
    id: step.id,
    label: t(step.labelKey),
    completed: completedSteps.has(step.id) || index < currentStepIndex
  }));

  // Navigation handlers
  const goToNextStep = useCallback(() => {
    setCompletedSteps(prev => new Set(prev).add(currentStepId));
    if (currentStepIndex < WIZARD_STEPS.length - 1) {
      setCurrentStepIndex(prev => prev + 1);
    }
  }, [currentStepIndex, currentStepId]);

  const goToPreviousStep = useCallback(() => {
    if (currentStepIndex > 0) {
      setCurrentStepIndex(prev => prev - 1);
    }
  }, [currentStepIndex]);

  // Skip directly to completion (used when credentials are imported)
  const goToCompletion = useCallback(() => {
    setCompletedSteps(prev => {
      const next = new Set(prev);
      next.add('welcome');
      next.add('import-credentials');
      next.add('claude-code');
      next.add('oauth');
      return next;
    });
    const completionIndex = WIZARD_STEPS.findIndex(s => s.id === 'completion');
    setCurrentStepIndex(completionIndex);
  }, []);

  // Reset wizard state
  const resetWizard = useCallback(() => {
    setCurrentStepIndex(0);
    setCompletedSteps(new Set());
  }, []);

  const skipWizard = useCallback(async () => {
    try {
      const result = await window.API.saveSettings({ onboardingCompleted: true });
      if (!result?.success) {
        console.error('Failed to save onboarding completion:', result?.error);
      }
    } catch (err) {
      console.error('Error saving onboarding completion:', err);
    }
    updateSettings({ onboardingCompleted: true });
    onOpenChange(false);
    resetWizard();
    // Trigger immediate refresh of Claude Code status badge
    window.dispatchEvent(new Event('claude-code-refresh'));
  }, [updateSettings, onOpenChange, resetWizard]);

  const finishWizard = useCallback(async () => {
    try {
      const result = await window.API.saveSettings({ onboardingCompleted: true });
      if (!result?.success) {
        console.error('Failed to save onboarding completion:', result?.error);
      }
    } catch (err) {
      console.error('Error saving onboarding completion:', err);
    }
    updateSettings({ onboardingCompleted: true });
    onOpenChange(false);
    resetWizard();
    // Trigger immediate refresh of Claude Code status badge
    window.dispatchEvent(new Event('claude-code-refresh'));
  }, [updateSettings, onOpenChange, resetWizard]);

  const handleOpenTaskCreator = useCallback(() => {
    if (onOpenTaskCreator) {
      onOpenChange(false);
      onOpenTaskCreator();
    }
  }, [onOpenTaskCreator, onOpenChange]);

  const handleOpenSettings = useCallback(() => {
    if (onOpenSettings) {
      finishWizard();
      onOpenSettings();
    }
  }, [onOpenSettings, finishWizard]);


  // Render current step content
  const renderStepContent = () => {
    switch (currentStepId) {
      case 'welcome':
        return (
          <WelcomeStep
            onGetStarted={goToNextStep}
            onSkip={skipWizard}
          />
        );
      case 'import-credentials':
        return (
          <ImportCredentialsStep
            onNext={goToNextStep}
            onSkipToCompletion={goToCompletion}
            onBack={goToPreviousStep}
            onSkip={skipWizard}
          />
        );
      case 'claude-code':
        return (
          <ClaudeCodeStep
            onNext={goToNextStep}
            onBack={goToPreviousStep}
            onSkip={goToNextStep}
          />
        );
      case 'oauth':
        return (
          <OAuthStep
            onNext={goToNextStep}
            onBack={goToPreviousStep}
            onSkip={skipWizard}
          />
        );
      case 'completion':
        return (
          <CompletionStep
            onFinish={finishWizard}
            onOpenTaskCreator={handleOpenTaskCreator}
            onOpenSettings={handleOpenSettings}
          />
        );
      default:
        return null;
    }
  };

  // Handle dialog close
  const handleOpenChange = useCallback((newOpen: boolean) => {
    if (!newOpen) {
      skipWizard();
    } else {
      onOpenChange(newOpen);
    }
  }, [skipWizard, onOpenChange]);

  return (
    <FullScreenDialog open={open} onOpenChange={handleOpenChange}>
      <FullScreenDialogContent>
        <FullScreenDialogHeader>
          <FullScreenDialogTitle className="flex items-center gap-3">
            <Wand2 className="h-6 w-6" />
            {t('wizard.title')}
          </FullScreenDialogTitle>
          <FullScreenDialogDescription>
            {t('wizard.description')}
          </FullScreenDialogDescription>

          {/* Progress indicator - show for auth steps */}
          {currentStepId !== 'welcome' && currentStepId !== 'completion' && (
            <div className="mt-6">
              <WizardProgress currentStep={currentStepIndex} steps={steps} />
            </div>
          )}
        </FullScreenDialogHeader>

        <FullScreenDialogBody>
          <ScrollArea className="h-full">
            {renderStepContent()}
          </ScrollArea>
        </FullScreenDialogBody>
      </FullScreenDialogContent>
    </FullScreenDialog>
  );
}
