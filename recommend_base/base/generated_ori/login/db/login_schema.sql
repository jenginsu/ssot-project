DROP TABLE IF EXISTS ssot.tbl_member;
CREATE TABLE ssot.tbl_member (
  user_id VARCHAR(255) NOT NULL,
  email VARCHAR(255) NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,
  PRIMARY KEY (user_id),
  UNIQUE KEY uq_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='회원 정보 테이블';