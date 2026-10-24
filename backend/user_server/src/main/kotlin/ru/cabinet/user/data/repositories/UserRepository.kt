package ru.cabinet.user.data.repositories

import org.springframework.data.jpa.repository.JpaRepository
import org.springframework.data.jpa.repository.Modifying
import org.springframework.data.jpa.repository.Query
import org.springframework.data.repository.query.Param
import org.springframework.transaction.annotation.Transactional
import ru.cabinet.user.data.models.UserEntity

interface UserRepository : JpaRepository<UserEntity, Long> {

    fun findUserEntityByLogin(login: String): UserEntity?

    @Modifying
    @Transactional
    @Query("update UserEntity u set u.refreshToken = :token, u.refreshTokenExpire = :expire where u.login = :login")
    fun updateUserByLogin(
        @Param("token") token: String?,
        @Param("expire") expire: java.time.LocalDateTime?,
        @Param("login") login: String
    )

    @Modifying
    @Transactional
    @Query("update UserEntity u set u.password = :password where u.login = :login")
    fun updatePasswordByLogin(@Param("login") login: String, @Param("password") password: String)

    fun existsByInn(inn: String): Boolean
    fun existsByOgrn(ogrn: String): Boolean
}