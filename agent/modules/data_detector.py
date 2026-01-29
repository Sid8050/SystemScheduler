"""
Sensitive Data Detector Module for Endpoint Security Agent

Provides:
- PII detection (SSN, credit cards, etc.)
- Custom pattern matching
- File content scanning
"""

import re
import mmap
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
from enum import Enum


class DataType(str, Enum):
    """Types of sensitive data."""
    CREDIT_CARD = "credit_card"
    SSN = "ssn"
    EMAIL = "email"
    PHONE = "phone"
    IP_ADDRESS = "ip_address"
    AWS_KEY = "aws_key"
    PRIVATE_KEY = "private_key"
    PASSWORD = "password"
    CUSTOM = "custom"


class Severity(str, Enum):
    """Severity levels for data detection."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class DetectionPattern:
    """Pattern for detecting sensitive data."""
    name: str
    data_type: DataType
    pattern: re.Pattern
    severity: Severity
    validator: Optional[Callable[[str], bool]] = None
    description: str = ""


@dataclass
class Detection:
    """A detected piece of sensitive data."""
    data_type: DataType
    pattern_name: str
    severity: Severity
    matched_text: str
    redacted_text: str
    line_number: int
    column: int
    context: str


@dataclass
class ScanResult:
    """Result of scanning a file."""
    file_path: str
    file_size: int
    scanned: bool
    error: Optional[str]
    detections: List[Detection]
    
    @property
    def has_sensitive_data(self) -> bool:
        return len(self.detections) > 0
    
    @property
    def detection_count(self) -> int:
        return len(self.detections)
    
    @property
    def highest_severity(self) -> Optional[Severity]:
        if not self.detections:
            return None
        severity_order = [Severity.LOW, Severity.MEDIUM, Severity.HIGH, Severity.CRITICAL]
        return max(self.detections, key=lambda d: severity_order.index(d.severity)).severity


class DataDetector:
    """
    Detect sensitive data in files using pattern matching.
    """
    
    # Credit card patterns (major card types)
    CREDIT_CARD_PATTERNS = [
        r'\b4[0-9]{12}(?:[0-9]{3})?\b',  # Visa
        r'\b5[1-5][0-9]{14}\b',           # MasterCard
        r'\b3[47][0-9]{13}\b',            # American Express
        r'\b6(?:011|5[0-9]{2})[0-9]{12}\b',  # Discover
        r'\b(?:2131|1800|35\d{3})\d{11}\b',  # JCB
    ]
    
    # US Social Security Number
    SSN_PATTERN = r'\b(?!000|666|9\d{2})\d{3}[-\s]?(?!00)\d{2}[-\s]?(?!0000)\d{4}\b'
    
    # Email pattern
    EMAIL_PATTERN = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    
    # Phone patterns (US)
    PHONE_PATTERNS = [
        r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b',
        r'\b\(\d{3}\)\s*\d{3}[-.\s]?\d{4}\b',
        r'\b\+1[-.\s]?\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b',
    ]
    
    # IP Address
    IP_PATTERN = r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b'
    
    # AWS Access Key
    AWS_KEY_PATTERN = r'\b(?:AKIA|ABIA|ACCA|ASIA)[A-Z0-9]{16}\b'
    
    # Private key indicators
    PRIVATE_KEY_PATTERNS = [
        r'-----BEGIN (?:RSA |DSA |EC )?PRIVATE KEY-----',
        r'-----BEGIN OPENSSH PRIVATE KEY-----',
    ]
    
    # Password-like patterns (common formats)
    PASSWORD_PATTERNS = [
        r'(?i)password\s*[=:]\s*["\']?[\w@#$%^&*!]+["\']?',
        r'(?i)passwd\s*[=:]\s*["\']?[\w@#$%^&*!]+["\']?',
        r'(?i)pwd\s*[=:]\s*["\']?[\w@#$%^&*!]+["\']?',
        r'(?i)secret\s*[=:]\s*["\']?[\w@#$%^&*!]+["\']?',
        r'(?i)api_key\s*[=:]\s*["\']?[\w-]+["\']?',
    ]
    
    def __init__(
        self,
        detect_credit_cards: bool = True,
        detect_ssn: bool = True,
        detect_email: bool = True,
        detect_phone: bool = True,
        detect_ip: bool = False,
        detect_aws_keys: bool = True,
        detect_private_keys: bool = True,
        detect_passwords: bool = True,
        custom_patterns: Optional[List[Dict]] = None,
        scan_extensions: Optional[List[str]] = None,
        max_file_size_mb: int = 50,
        on_detection: Optional[Callable[[str, Detection], None]] = None
    ):
        self.max_file_size = max_file_size_mb * 1024 * 1024
        self.scan_extensions = set(
            ext.lower() if ext.startswith('.') else f'.{ext.lower()}'
            for ext in (scan_extensions or [
                '.txt', '.csv', '.json', '.xml', '.yaml', '.yml',
                '.md', '.log', '.conf', '.config', '.ini', '.env',
                '.py', '.js', '.ts', '.java', '.cs', '.php', '.rb',
                '.sql', '.html', '.htm'
            ])
        )
        self.on_detection = on_detection
        
        # Build patterns list
        self.patterns: List[DetectionPattern] = []
        
        if detect_credit_cards:
            for i, pattern in enumerate(self.CREDIT_CARD_PATTERNS):
                self.patterns.append(DetectionPattern(
                    name=f"credit_card_{i}",
                    data_type=DataType.CREDIT_CARD,
                    pattern=re.compile(pattern),
                    severity=Severity.CRITICAL,
                    validator=self._validate_credit_card,
                    description="Credit card number"
                ))
        
        if detect_ssn:
            self.patterns.append(DetectionPattern(
                name="ssn",
                data_type=DataType.SSN,
                pattern=re.compile(self.SSN_PATTERN),
                severity=Severity.CRITICAL,
                description="US Social Security Number"
            ))
        
        if detect_email:
            self.patterns.append(DetectionPattern(
                name="email",
                data_type=DataType.EMAIL,
                pattern=re.compile(self.EMAIL_PATTERN),
                severity=Severity.LOW,
                description="Email address"
            ))
        
        if detect_phone:
            for i, pattern in enumerate(self.PHONE_PATTERNS):
                self.patterns.append(DetectionPattern(
                    name=f"phone_{i}",
                    data_type=DataType.PHONE,
                    pattern=re.compile(pattern),
                    severity=Severity.MEDIUM,
                    description="Phone number"
                ))
        
        if detect_ip:
            self.patterns.append(DetectionPattern(
                name="ip_address",
                data_type=DataType.IP_ADDRESS,
                pattern=re.compile(self.IP_PATTERN),
                severity=Severity.LOW,
                validator=self._validate_ip,
                description="IP address"
            ))
        
        if detect_aws_keys:
            self.patterns.append(DetectionPattern(
                name="aws_key",
                data_type=DataType.AWS_KEY,
                pattern=re.compile(self.AWS_KEY_PATTERN),
                severity=Severity.CRITICAL,
                description="AWS Access Key"
            ))
        
        if detect_private_keys:
            for i, pattern in enumerate(self.PRIVATE_KEY_PATTERNS):
                self.patterns.append(DetectionPattern(
                    name=f"private_key_{i}",
                    data_type=DataType.PRIVATE_KEY,
                    pattern=re.compile(pattern),
                    severity=Severity.CRITICAL,
                    description="Private key"
                ))
        
        if detect_passwords:
            for i, pattern in enumerate(self.PASSWORD_PATTERNS):
                self.patterns.append(DetectionPattern(
                    name=f"password_{i}",
                    data_type=DataType.PASSWORD,
                    pattern=re.compile(pattern),
                    severity=Severity.HIGH,
                    description="Password or secret"
                ))
        
        # Add custom patterns
        if custom_patterns:
            for cp in custom_patterns:
                self.patterns.append(DetectionPattern(
                    name=cp.get('name', 'custom'),
                    data_type=DataType.CUSTOM,
                    pattern=re.compile(cp['pattern']),
                    severity=Severity(cp.get('severity', 'medium')),
                    description=cp.get('description', '')
                ))
    
    def _validate_credit_card(self, number: str) -> bool:
        """Validate credit card using Luhn algorithm."""
        # Remove non-digits
        digits = re.sub(r'\D', '', number)
        
        if len(digits) < 13 or len(digits) > 19:
            return False
        
        # Luhn algorithm
        total = 0
        for i, digit in enumerate(reversed(digits)):
            n = int(digit)
            if i % 2 == 1:
                n *= 2
                if n > 9:
                    n -= 9
            total += n
        
        return total % 10 == 0
    
    def _validate_ip(self, ip: str) -> bool:
        """Validate IP address (exclude common false positives)."""
        # Exclude localhost and private ranges that are commonly used
        if ip.startswith('127.') or ip.startswith('0.'):
            return False
        if ip == '255.255.255.255':
            return False
        return True
    
    def _redact(self, text: str, data_type: DataType) -> str:
        """Redact sensitive data."""
        if data_type == DataType.CREDIT_CARD:
            # Show last 4 digits
            digits = re.sub(r'\D', '', text)
            return '*' * (len(digits) - 4) + digits[-4:]
        elif data_type == DataType.SSN:
            return '***-**-' + text[-4:]
        elif data_type == DataType.EMAIL:
            parts = text.split('@')
            if len(parts) == 2:
                return parts[0][0] + '***@' + parts[1]
            return '***'
        elif data_type == DataType.PHONE:
            digits = re.sub(r'\D', '', text)
            return '***-***-' + digits[-4:]
        elif data_type in (DataType.PASSWORD, DataType.AWS_KEY, DataType.PRIVATE_KEY):
            return '[REDACTED]'
        else:
            # Generic redaction
            if len(text) > 4:
                return text[:2] + '*' * (len(text) - 4) + text[-2:]
            return '*' * len(text)
    
    def _get_context(self, content: str, start: int, end: int, context_chars: int = 50) -> str:
        """Get surrounding context for a match."""
        ctx_start = max(0, start - context_chars)
        ctx_end = min(len(content), end + context_chars)
        
        context = content[ctx_start:ctx_end]
        
        # Clean up context
        context = context.replace('\n', ' ').replace('\r', ' ')
        context = re.sub(r'\s+', ' ', context)
        
        if ctx_start > 0:
            context = '...' + context
        if ctx_end < len(content):
            context = context + '...'
        
        return context
    
    def _get_line_col(self, content: str, position: int) -> Tuple[int, int]:
        """Get line number and column for a position."""
        lines = content[:position].split('\n')
        line_num = len(lines)
        col = len(lines[-1]) + 1 if lines else 1
        return line_num, col
    
    def scan_text(self, content: str, source: str = "") -> List[Detection]:
        """
        Scan text content for sensitive data.
        
        Args:
            content: Text to scan
            source: Source identifier (e.g., file path)
            
        Returns:
            List of detections
        """
        detections = []
        seen_matches: Set[Tuple[str, int]] = set()  # Dedupe by (text, position)
        
        for pattern in self.patterns:
            for match in pattern.pattern.finditer(content):
                matched_text = match.group()
                position = match.start()
                
                # Skip if we've already detected this exact match
                key = (matched_text, position)
                if key in seen_matches:
                    continue
                seen_matches.add(key)
                
                # Validate if validator exists
                if pattern.validator and not pattern.validator(matched_text):
                    continue
                
                line_num, col = self._get_line_col(content, position)
                
                detection = Detection(
                    data_type=pattern.data_type,
                    pattern_name=pattern.name,
                    severity=pattern.severity,
                    matched_text=matched_text,
                    redacted_text=self._redact(matched_text, pattern.data_type),
                    line_number=line_num,
                    column=col,
                    context=self._get_context(content, match.start(), match.end())
                )
                
                detections.append(detection)
                
                # Callback
                if self.on_detection:
                    self.on_detection(source, detection)
        
        return detections
    
    def scan_file(self, file_path: str) -> ScanResult:
        """
        Scan a file for sensitive data.
        
        Args:
            file_path: Path to file
            
        Returns:
            ScanResult with detections
        """
        path = Path(file_path)
        
        # Check if file exists
        if not path.exists():
            return ScanResult(
                file_path=file_path,
                file_size=0,
                scanned=False,
                error="File not found",
                detections=[]
            )
        
        # Check file size
        file_size = path.stat().st_size
        if file_size > self.max_file_size:
            return ScanResult(
                file_path=file_path,
                file_size=file_size,
                scanned=False,
                error=f"File too large ({file_size} bytes)",
                detections=[]
            )
        
        # Check extension
        if self.scan_extensions and path.suffix.lower() not in self.scan_extensions:
            return ScanResult(
                file_path=file_path,
                file_size=file_size,
                scanned=False,
                error=f"Extension not in scan list",
                detections=[]
            )
        
        try:
            # Read file content
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Scan content
            detections = self.scan_text(content, file_path)
            
            return ScanResult(
                file_path=file_path,
                file_size=file_size,
                scanned=True,
                error=None,
                detections=detections
            )
        
        except Exception as e:
            return ScanResult(
                file_path=file_path,
                file_size=file_size,
                scanned=False,
                error=str(e),
                detections=[]
            )
    
    def scan_directory(
        self,
        directory: str,
        recursive: bool = True,
        progress_callback: Optional[Callable[[str, int, int], None]] = None
    ) -> List[ScanResult]:
        """
        Scan all files in a directory.
        
        Args:
            directory: Directory path
            recursive: Scan subdirectories
            progress_callback: Progress callback (file, scanned, total)
            
        Returns:
            List of scan results
        """
        results = []
        dir_path = Path(directory)
        
        # Get list of files
        if recursive:
            files = list(dir_path.rglob('*'))
        else:
            files = list(dir_path.glob('*'))
        
        # Filter to files only
        files = [f for f in files if f.is_file()]
        total = len(files)
        
        for i, file_path in enumerate(files):
            result = self.scan_file(str(file_path))
            results.append(result)
            
            if progress_callback:
                progress_callback(str(file_path), i + 1, total)
        
        return results
    
    def get_summary(self, results: List[ScanResult]) -> Dict:
        """Get summary of scan results."""
        total_files = len(results)
        scanned_files = sum(1 for r in results if r.scanned)
        files_with_detections = sum(1 for r in results if r.has_sensitive_data)
        total_detections = sum(r.detection_count for r in results)
        
        # Count by type
        by_type: Dict[str, int] = {}
        by_severity: Dict[str, int] = {}
        
        for result in results:
            for detection in result.detections:
                by_type[detection.data_type.value] = by_type.get(detection.data_type.value, 0) + 1
                by_severity[detection.severity.value] = by_severity.get(detection.severity.value, 0) + 1
        
        return {
            'total_files': total_files,
            'scanned_files': scanned_files,
            'files_with_detections': files_with_detections,
            'total_detections': total_detections,
            'by_type': by_type,
            'by_severity': by_severity
        }
