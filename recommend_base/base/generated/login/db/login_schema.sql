DROP TABLE IF EXISTS ssot.tbl_member;
CREATE TABLE ssot.tbl_member (
  user_id VARCHAR(20) NOT NULL COMMENT '사용자 ID',
  email VARCHAR(255) NOT NULL UNIQUE COMMENT '이메일',
  password_hash VARCHAR(255) NOT NULL COMMENT '비밀번호 해시',
  fail_count INT NOT NULL DEFAULT 0 COMMENT '연속 로그인 실패 횟수',
  is_locked TINYINT(1) NOT NULL DEFAULT 0 COMMENT '계정 잠금 여부',
  locked_at DATETIME NULL COMMENT '계정 잠금 시각',
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,
  PRIMARY KEY (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='회원 정보';