export type AssigneeAvatarPresentation =
  | { kind: "avatar"; avatarUrl: string; displayName: string | undefined }
  | { kind: "initial"; initial: string }
  | { kind: "placeholder" };

/** Resolve whether the assignee cell should show an image, an initial, or a placeholder icon. */
export const getAssigneeAvatarPresentation = (
  avatarUrl: string | undefined,
  displayName: string | undefined
): AssigneeAvatarPresentation => {
  if (avatarUrl) return { kind: "avatar", avatarUrl, displayName };

  const initial = displayName?.[0];
  if (initial) return { kind: "initial", initial };

  return { kind: "placeholder" };
};
