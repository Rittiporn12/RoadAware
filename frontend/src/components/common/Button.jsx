import Icon from "./Icon";
export default function Button({
  children,
  icon,
  trailingIcon,
  variant = "primary",
  className = "",
}) {
  return (
    <button type="button" className={`button button--${variant} ${className}`}>
      {icon && <Icon name={icon} />}
      <span>{children}</span>
      {trailingIcon && <Icon name={trailingIcon} size={20} />}
    </button>
  );
}
